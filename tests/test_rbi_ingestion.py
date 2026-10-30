import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import faiss
import numpy as np

from backend.app.services import rbi_ingest, rag_pipeline, rbi_scraper
from backend.app.services.rebuild_rbi_index import (
    _validate_staged_index,
    build_staged_rbi_index,
)
from backend.app.services.rbi_ingest import prepare_rbi_chunks


class MockResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeVectorStore:
    def __init__(self, index_path, metadata_path):
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.documents = []

    def add_documents(self, documents):
        self.documents.extend(documents)

    def save(self):
        index = faiss.IndexFlatL2(2)
        vectors = np.zeros((len(self.documents), 2), dtype=np.float32)
        index.add(vectors)
        faiss.write_index(index, str(self.index_path))
        self.metadata_path.write_text(
            json.dumps(self.documents),
            encoding="utf-8",
        )
        return True


class FakeSearchVectorStore:
    def __init__(self, documents):
        self.documents = documents
        self.search_calls = []

    def is_ready(self):
        return True

    def search(self, query, top_k):
        self.search_calls.append((query, top_k))
        return self.documents[:top_k]


class RbiIngestionTests(unittest.TestCase):
    def test_broad_payment_security_retrieval_deduplicates_by_url_in_rank_order(self):
        documents = [
            {
                "text": "Urban co-operative controls passage",
                "metadata": {
                    "title": "Urban Co-operative Banks Digital Payment Security Controls",
                    "url": "https://rbi.example/ucb.pdf",
                    "category": "master_direction",
                },
                "score": 0.4597,
            },
            {
                "text": "Small finance controls passage one",
                "metadata": {
                    "title": "Small Finance Banks Digital Payment Security Controls",
                    "url": "https://rbi.example/sfb.pdf",
                    "category": "master_direction",
                },
                "score": 0.5566,
            },
            {
                "text": "Small finance controls passage two",
                "metadata": {
                    "title": "Small Finance Banks Digital Payment Security Controls",
                    "url": "https://rbi.example/sfb.pdf",
                    "category": "master_direction",
                },
                "score": 0.5585,
            },
            {
                "text": "Payments bank controls passage",
                "metadata": {
                    "title": "Payments Banks Digital Payment Security Controls",
                    "url": "https://rbi.example/pb.pdf",
                    "category": "master_direction",
                },
                "score": 0.5758,
            },
        ]
        vector_store = FakeSearchVectorStore(documents)
        pipeline = rag_pipeline.RAGPipeline(vector_store, top_k=3)

        results = pipeline._retrieve_rbi(
            "What are the RBI's digital-payment security controls?"
        )

        self.assertEqual(vector_store.search_calls, [
            ("What are the RBI's digital-payment security controls?", 12),
        ])
        self.assertEqual(
            [result["metadata"]["url"] for result in results],
            [
                "https://rbi.example/ucb.pdf",
                "https://rbi.example/sfb.pdf",
                "https://rbi.example/pb.pdf",
            ],
        )
        self.assertEqual(
            [result["score"] for result in results],
            [0.4597, 0.5566, 0.5758],
        )
        self.assertEqual(
            results[1]["metadata"],
            documents[1]["metadata"],
        )
        self.assertEqual(results[1]["text"], documents[1]["text"])

    def test_commercial_bank_query_finds_document_ranked_sixth(self):
        documents = [
            {
                "text": f"{institution} passage {rank}",
                "metadata": {
                    "title": f"{institution} Digital Payment Security Directions",
                    "url": f"https://rbi.example/{institution.lower().replace(' ', '-')}-{rank}.pdf",
                    "category": "master_direction",
                },
                "score": rank / 10,
            }
            for rank, institution in enumerate(
                [
                    "Small Finance Banks",
                    "Payments Banks",
                    "Urban Co-operative Banks",
                    "Non-Banking Financial Companies",
                    "Small Finance Banks",
                    "Commercial Banks",
                    "Payments Banks",
                    "Commercial Banks",
                    "Urban Co-operative Banks",
                    "Commercial Banks",
                    "Payments Banks",
                    "Small Finance Banks",
                ],
                1,
            )
        ]
        vector_store = FakeSearchVectorStore(documents)
        pipeline = rag_pipeline.RAGPipeline(vector_store, top_k=2)

        results = pipeline._retrieve_rbi(
            "What are the RBI's digital payment security requirements for Commercial Banks?"
        )

        self.assertEqual(vector_store.search_calls[0][1], 12)
        self.assertEqual(
            [result["metadata"]["title"] for result in results],
            [
                "Commercial Banks Digital Payment Security Directions",
                "Commercial Banks Digital Payment Security Directions",
            ],
        )
        self.assertEqual([result["score"] for result in results], [0.6, 0.8])
        self.assertEqual(results, [documents[5], documents[7]])
        self.assertEqual(len(results), pipeline.top_k)

    def test_unrelated_query_uses_existing_top_k_path(self):
        documents = [
            {
                "text": "First passage",
                "metadata": {"title": "RBI KYC Directions"},
                "score": 0.1,
            },
        ]
        vector_store = FakeSearchVectorStore(documents)
        pipeline = rag_pipeline.RAGPipeline(vector_store, top_k=3)

        results = pipeline._retrieve_rbi("What are the RBI KYC requirements?")

        self.assertEqual(vector_store.search_calls[0][1], 3)
        self.assertEqual(results, documents)

    def test_commercial_bank_scope_keeps_matching_and_ambiguous_titles(self):
        documents = [
            {
                "text": "Commercial-bank direction text",
                "metadata": {"title": "Commercial Banks Capital Directions"},
                "score": 0.1,
            },
            {
                "text": "Generic bank direction text",
                "metadata": {"title": "Prudential Directions for Banks"},
                "score": 0.2,
            },
            {
                "text": "Small-finance-bank direction text",
                "metadata": {
                    "title": "Small Finance Banks Digital Payment Directions"
                },
                "score": 0.3,
            },
        ]
        pipeline = rag_pipeline.RAGPipeline(
            FakeSearchVectorStore(documents),
            auto_ingest=False,
        )

        with patch.object(
            rag_pipeline,
            "ask_llm",
            return_value="Answer",
        ) as ask_llm:
            response = pipeline.answer(
                "What do the RBI directions say about commercial banks?"
            )

        self.assertEqual(response["answer"], "Answer")
        prompt = ask_llm.call_args.args[0]
        self.assertIn("Commercial Banks Capital Directions", prompt)
        self.assertIn("Prudential Directions for Banks", prompt)
        self.assertNotIn("Small Finance Banks Digital Payment Directions", prompt)
        self.assertEqual(
            [source["title"] for source in response["sources"]],
            [
                "Commercial Banks Capital Directions",
                "Prudential Directions for Banks",
            ],
        )

    def test_commercial_bank_scope_returns_limitation_without_llm_when_all_mismatch(self):
        documents = [
            {
                "text": "Urban cooperative bank direction text",
                "metadata": {
                    "title": "Urban Co-operative Banks Directions"
                },
                "score": 0.1,
            },
            {
                "text": "Payments bank direction text",
                "metadata": {"title": "Payments Banks Directions"},
                "score": 0.2,
            },
        ]
        pipeline = rag_pipeline.RAGPipeline(
            FakeSearchVectorStore(documents),
            auto_ingest=False,
        )

        with patch.object(rag_pipeline, "ask_llm") as ask_llm:
            response = pipeline.answer(
                "What do the RBI directions say about commercial banks?"
            )

        self.assertIn("not enough relevant information", response["answer"])
        self.assertEqual(response["sources"], [])
        ask_llm.assert_not_called()

    def test_other_queries_do_not_apply_commercial_bank_scope_filter(self):
        documents = [
            {
                "text": "Small-finance-bank direction text",
                "metadata": {
                    "title": "Small Finance Banks Digital Payment Directions"
                },
                "score": 0.1,
            },
        ]
        pipeline = rag_pipeline.RAGPipeline(
            FakeSearchVectorStore(documents),
            auto_ingest=False,
        )

        with patch.object(
            rag_pipeline,
            "ask_llm",
            return_value="Answer",
        ) as ask_llm:
            response = pipeline.answer("What are the RBI digital payment directions?")

        self.assertEqual(response["answer"], "Answer")
        self.assertIn(
            "Small Finance Banks Digital Payment Directions",
            ask_llm.call_args.args[0],
        )

    @staticmethod
    def _listing_row(title, pdf_path, detail_id):
        return (
            "<tr>"
            f'<td><a href="/detail?id={detail_id}">{title}</a></td>'
            f'<td><a href="{pdf_path}"><img alt="PDF document"></a></td>'
            "</tr>"
        )

    def test_priority_title_matching_covers_requested_topics(self):
        titles = [
            "Digital Payments: Authorization and Security",
            "Reserve Bank of India (Small Finance Banks – Digital Payment Security Controls) Directions, 2026",
            "Reserve Bank of India (Payments Banks – Digital Payment Security Controls) Directions, 2026",
            "Reserve Bank of India (Urban Co-operative Banks – Digital Payment Security Controls) Directions, 2026",
            "Reserve Bank of India (Non-Banking Financial Companies – Digital Payment Security Controls) Directions, 2026",
            "Digital Payments – E-mandate Framework, 2026",
            "Authentication mechanisms for digital payment transactions Directions, 2025",
            "Cyber Resilience and Digital Payment Security Controls for non-bank Payment System Operators",
            "Guidelines on Digital Lending",
            "Monetary Policy Committee Resolution",
            "MPC Decision on the Policy Rate",
            "Monetary Policy Statement",
            "Reserve Bank of India (Commercial Banks) Directions, 2026",
        ]

        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(rbi_scraper._is_priority_title(title))

    def test_priority_selection_prefers_digital_topics_over_many_bank_directions(self):
        source_items = [
            [
                {
                    "title": f"Press Release {number}",
                    "pdf_url": f"https://rbi.example/press/{number}.pdf",
                    "category": "press_release",
                }
                for number in range(10)
            ]
            + [
                {
                    "title": "Monetary Policy Committee Resolution",
                    "pdf_url": "https://rbi.example/press/mpc.pdf",
                    "category": "press_release",
                }
            ],
            [
                {
                    "title": f"Banking Circular {number}",
                    "pdf_url": f"https://rbi.example/notifications/{number}.pdf",
                    "category": "notification_or_circular",
                }
                for number in range(10)
            ]
            + [
                {
                    "title": "Guidelines on Digital Lending",
                    "pdf_url": "https://rbi.example/notifications/lending.pdf",
                    "category": "notification_or_circular",
                }
            ],
            [
                {
                    "title": f"Commercial Banks Master Directions {number}",
                    "pdf_url": f"https://rbi.example/directions/{number}.pdf",
                    "category": "master_direction",
                }
                for number in range(10)
            ]
            + [
                {
                    "title": "Small Finance Banks – Digital Payment Security Controls Directions",
                    "pdf_url": "https://rbi.example/directions/sfb-payments.pdf",
                    "category": "master_direction",
                },
                {
                    "title": "Payments Banks – Digital Payment Security Controls Directions",
                    "pdf_url": "https://rbi.example/directions/payments-banks.pdf",
                    "category": "master_direction",
                },
            ],
        ]

        selected = rbi_scraper._select_pdf_items(source_items, limit=8)

        self.assertEqual(len(selected), 8)
        category_counts = {
            category: sum(item["category"] == category for item in selected)
            for category in (
                "press_release",
                "notification_or_circular",
                "master_direction",
            )
        }
        self.assertEqual(
            set(category_counts),
            {"press_release", "notification_or_circular", "master_direction"},
        )
        self.assertLessEqual(
            max(category_counts.values()) - min(category_counts.values()),
            1,
        )
        titles = {item["title"] for item in selected}
        self.assertIn("Monetary Policy Committee Resolution", titles)
        self.assertIn("Guidelines on Digital Lending", titles)
        self.assertIn(
            "Small Finance Banks – Digital Payment Security Controls Directions",
            titles,
        )
        self.assertIn(
            "Payments Banks – Digital Payment Security Controls Directions",
            titles,
        )
        self.assertLessEqual(
            sum(
                item["title"].startswith("Commercial Banks")
                for item in selected
            ),
            3,
        )

    def test_selection_never_exceeds_requested_limit(self):
        source_items = [
            [
                {
                    "title": f"Reserve Bank of India (Commercial Banks) Directions, {number}",
                    "pdf_url": f"https://rbi.example/directions/{number}.pdf",
                    "category": "master_direction",
                }
                for number in range(30)
            ]
        ]

        selected = rbi_scraper._select_pdf_items(source_items, limit=7)

        self.assertEqual(len(selected), 7)
        self.assertEqual(len({item["pdf_url"] for item in selected}), 7)

    def test_unrelated_titles_are_not_priority_matches(self):
        titles = [
            "Treasury Bills: Full Auction Result",
            "Money Market Operations as on October 28, 2026",
            "Agency Bank Payment of Commission Directions",
            "Commercial Banks Prudential Norms on Capital Adequacy",
        ]

        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(rbi_scraper._is_priority_title(title))

    def test_priority_selection_preserves_each_available_source_category(self):
        sources = [
            {
                "name": "Press Releases",
                "category": "press_release",
                "url": "https://rbi.example/press",
            },
            {
                "name": "Notifications",
                "category": "notification_or_circular",
                "url": "https://rbi.example/notifications",
            },
            {
                "name": "Master Directions",
                "category": "master_direction",
                "url": "https://rbi.example/directions",
            },
        ]
        pages = {
            sources[0]["url"]: (
                "<table>"
                + self._listing_row(
                    "Treasury Bills Auction Results",
                    "/press/auction.pdf",
                    "press-auction",
                )
                + self._listing_row(
                    "MPC Resolution on Monetary Policy",
                    "/press/mpc.pdf",
                    "press-mpc",
                )
                + "</table>"
            ),
            sources[1]["url"]: (
                "<table>"
                + self._listing_row(
                    "UAPA List Update",
                    "/notifications/uapa.pdf",
                    "notification-uapa",
                )
                + self._listing_row(
                    "Digital Lending Directions",
                    "/notifications/lending.pdf",
                    "notification-lending",
                )
                + "</table>"
            ),
            sources[2]["url"]: (
                "<table>"
                + self._listing_row(
                    "Primary Dealer Guidelines",
                    "/directions/primary-dealers.pdf",
                    "direction-pd",
                )
                + self._listing_row(
                    "Commercial Banks Master Directions",
                    "/directions/commercial-banks.pdf",
                    "direction-commercial",
                )
                + "</table>"
            ),
        }

        with (
            patch.object(rbi_scraper, "RBI_SOURCES", sources),
            patch.object(
                rbi_scraper.requests,
                "get",
                side_effect=lambda url, timeout: MockResponse(pages[url]),
            ),
        ):
            links = rbi_scraper.fetch_rbi_pdf_links(limit=3)

        self.assertEqual(
            {item["category"] for item in links},
            {"press_release", "notification_or_circular", "master_direction"},
        )
        self.assertEqual(
            {item["title"] for item in links},
            {
                "MPC Resolution on Monetary Policy",
                "Digital Lending Directions",
                "Commercial Banks Master Directions",
            },
        )

    def test_selection_fills_limit_when_fewer_matching_titles_exist(self):
        sources = [
            {
                "name": "Notifications",
                "category": "notification_or_circular",
                "url": "https://rbi.example/notifications",
            },
        ]
        pages = {
            sources[0]["url"]: (
                "<table>"
                + self._listing_row(
                    "Digital Payments Rules",
                    "/notifications/payments.pdf",
                    "notification-payments",
                )
                + self._listing_row(
                    "General Banking Circular",
                    "/notifications/circular.pdf",
                    "notification-circular",
                )
                + "</table>"
            ),
        }

        with (
            patch.object(rbi_scraper, "RBI_SOURCES", sources),
            patch.object(
                rbi_scraper.requests,
                "get",
                side_effect=lambda url, timeout: MockResponse(pages[url]),
            ),
        ):
            links = rbi_scraper.fetch_rbi_pdf_links(limit=5)

        self.assertEqual(
            [item["title"] for item in links],
            ["Digital Payments Rules", "General Banking Circular"],
        )

    def test_scraper_uses_adjacent_listing_titles_for_each_source_category(self):
        sources = [
            {
                "name": "Notifications",
                "category": "notification_or_circular",
                "url": "https://rbi.example/notifications",
            },
            {
                "name": "Press Releases",
                "category": "press_release",
                "url": "https://rbi.example/press",
            },
            {
                "name": "Master Directions",
                "category": "master_direction",
                "url": "https://rbi.example/directions",
            },
        ]
        rows = [
            (
                "Reserve Bank of India (Commercial Banks) Directions, 2026",
                "/docs/notification.pdf",
            ),
            (
                "RBI issues updated digital payment guidelines",
                "https://rbi.example/docs/press-release.pdf",
            ),
            (
                "Master Direction – Commercial Banks, 2026",
                "../docs/master-direction.pdf",
            ),
        ]
        pages = {
            source["url"]: (
                "<table><tr>"
                f'<td><a href="/detail?id={number}">{title}</a></td>'
                f'<td><a href="{pdf_url}"><img alt="PDF document"></a></td>'
                "</tr></table>"
            )
            for number, (source, (title, pdf_url)) in enumerate(
                zip(sources, rows),
                start=1,
            )
        }

        with (
            patch.object(rbi_scraper, "RBI_SOURCES", sources),
            patch.object(
                rbi_scraper.requests,
                "get",
                side_effect=lambda url, timeout: MockResponse(pages[url]),
            ),
        ):
            links = rbi_scraper.fetch_rbi_pdf_links(limit=3)

        self.assertEqual(
            [
                (item["title"], item["pdf_url"], item["category"])
                for item in links
            ],
            [
                (
                    rows[0][0],
                    "https://rbi.example/docs/notification.pdf",
                    "notification_or_circular",
                ),
                (
                    rows[1][0],
                    rows[1][1],
                    "press_release",
                ),
                (
                    rows[2][0],
                    "https://rbi.example/docs/master-direction.pdf",
                    "master_direction",
                ),
            ],
        )

    def test_scraper_reads_registered_pages_and_accepts_only_unique_pdfs(self):
        sources = [
            {
                "name": "Circulars",
                "category": "notification_or_circular",
                "url": "https://rbi.example/circulars",
            },
            {
                "name": "Master Directions",
                "category": "master_direction",
                "url": "https://rbi.example/directions",
            },
            {
                "name": "Circular alias",
                "category": "notification_or_circular",
                "url": "https://rbi.example/circulars",
            },
        ]
        pages = {
            sources[0]["url"]: (
                '<a href="/docs/circular.pdf">Circular A</a>'
                '<a href="/Scripts/details.aspx">Details</a>'
            ),
            sources[1]["url"]: (
                '<a href="https://rbi.example/docs/circular.pdf">Duplicate</a>'
                '<a href="../docs/direction.pdf">Direction B</a>'
            ),
        }

        with (
            patch.object(rbi_scraper, "RBI_SOURCES", sources),
            patch.object(
                rbi_scraper.requests,
                "get",
                side_effect=lambda url, timeout: MockResponse(pages[url]),
            ) as get,
        ):
            links = rbi_scraper.fetch_rbi_pdf_links(limit=10)

        self.assertEqual(
            [item["pdf_url"] for item in links],
            [
                "https://rbi.example/docs/circular.pdf",
                "https://rbi.example/docs/direction.pdf",
            ],
        )
        self.assertEqual(
            [item["category"] for item in links],
            ["notification_or_circular", "master_direction"],
        )
        self.assertEqual(get.call_count, 2)

    def test_limit_is_shared_across_sources_instead_of_favoring_first_page(self):
        sources = [
            {
                "name": "Press Releases",
                "category": "press_release",
                "url": "https://rbi.example/press",
            },
            {
                "name": "Master Directions",
                "category": "master_direction",
                "url": "https://rbi.example/directions",
            },
        ]
        pages = {
            sources[0]["url"]: "".join(
                f'<a href="/press/{number}.pdf">Press {number}</a>'
                for number in range(5)
            ),
            sources[1]["url"]: (
                '<a href="/directions/master.pdf">Master Direction</a>'
            ),
        }

        with (
            patch.object(rbi_scraper, "RBI_SOURCES", sources),
            patch.object(
                rbi_scraper.requests,
                "get",
                side_effect=lambda url, timeout: MockResponse(pages[url]),
            ),
        ):
            links = rbi_scraper.fetch_rbi_pdf_links(limit=3)

        self.assertEqual(
            [item["category"] for item in links],
            ["press_release", "master_direction", "press_release"],
        )

    def test_documents_keep_endpoint_fields_and_category(self):
        pdf = {
            "title": "Digital Lending Directions",
            "pdf_url": "https://rbi.example/digital-lending.pdf",
            "category": "master_direction",
        }
        with (
            patch.object(rbi_scraper, "fetch_rbi_pdf_links", return_value=[pdf]),
            patch.object(
                rbi_scraper,
                "extract_text_from_pdf_url",
                return_value="A" * 600,
            ),
        ):
            documents = rbi_scraper.fetch_all_rbi_documents(limit=1)

        self.assertEqual(
            documents,
            [
                {
                    "title": pdf["title"],
                    "source": "RBI",
                    "url": pdf["pdf_url"],
                    "category": "master_direction",
                    "content": "A" * 600,
                }
            ],
        )

    def test_generic_listing_title_uses_pdf_heading_and_keeps_provenance(self):
        pdf = {
            "title": "Master Directions",
            "source_name": "Master Directions",
            "pdf_url": "https://rbi.example/directions.pdf",
            "category": "master_direction",
        }
        content = (
            "January 12, 2026\n"
            "Reserve Bank of India\n"
            "Commercial Banks - Digital Lending Directions, 2026\n"
            + "Detailed direction content. " * 30
        )
        with (
            patch.object(rbi_scraper, "fetch_rbi_pdf_links", return_value=[pdf]),
            patch.object(
                rbi_scraper,
                "extract_text_from_pdf_url",
                return_value=content,
            ),
        ):
            documents = rbi_scraper.fetch_all_rbi_documents(limit=1)

        self.assertEqual(
            documents[0],
            {
                "title": "Commercial Banks - Digital Lending Directions, 2026",
                "source": "RBI",
                "url": pdf["pdf_url"],
                "category": "master_direction",
                "content": content,
            },
        )

    def test_chunking_preserves_document_metadata(self):
        content = "digital lending requirements " * 40
        chunks = prepare_rbi_chunks(
            [
                {
                    "title": "Digital Lending Directions",
                    "url": "https://rbi.example/digital-lending.pdf",
                    "source": "RBI",
                    "category": "master_direction",
                    "content": content,
                }
            ]
        )

        self.assertGreater(len(chunks), 0)
        self.assertEqual(
            chunks[0]["metadata"],
            {
                "title": "Digital Lending Directions",
                "url": "https://rbi.example/digital-lending.pdf",
                "source": "RBI",
                "category": "master_direction",
                "type": "rbi",
            },
        )

    def test_duplicate_normalized_chunks_removed_only_within_each_document(self):
        repeated_chunk = "First distinct passage."
        second_passage = "Another distinct passage."
        documents = [
            {
                "title": "Document One",
                "url": "https://rbi.example/one.pdf",
                "source": "RBI",
                "category": "circular",
                "content": "first document",
            },
            {
                "title": "Document Two",
                "url": "https://rbi.example/two.pdf",
                "source": "RBI",
                "category": "circular",
                "content": "second document",
            },
        ]
        with patch.object(
            rbi_ingest,
            "chunk_text",
            side_effect=[
                [repeated_chunk, "  FIRST   DISTINCT PASSAGE.  ", second_passage],
                [repeated_chunk],
            ],
        ):
            chunks = prepare_rbi_chunks(documents)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(
            [chunk["metadata"]["url"] for chunk in chunks],
            [
                "https://rbi.example/one.pdf",
                "https://rbi.example/one.pdf",
                "https://rbi.example/two.pdf",
            ],
        )

    def test_builder_validates_pair_and_leaves_active_files_untouched(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            active_index = root / "active.index"
            active_metadata = root / "active.json"
            active_index.write_bytes(b"existing index")
            active_metadata.write_text("existing metadata", encoding="utf-8")
            before_active = (
                active_index.read_bytes(),
                active_metadata.read_text(encoding="utf-8"),
            )

            documents = [
                {
                    "title": "RBI Circular",
                    "url": "https://rbi.example/circular.pdf",
                    "source": "RBI",
                    "category": "notification_or_circular",
                    "content": "RBI circular content " * 50,
                }
            ]
            stage_dir, count = build_staged_rbi_index(
                limit=1,
                staging_root=root / "staging",
                document_fetcher=Mock(return_value=documents),
                vector_store_factory=FakeVectorStore,
            )

            self.assertTrue((stage_dir / "rbi.index").is_file())
            self.assertTrue((stage_dir / "rbi_docs.json").is_file())
            self.assertEqual(
                count,
                _validate_staged_index(
                    stage_dir / "rbi.index",
                    stage_dir / "rbi_docs.json",
                ),
            )
            self.assertEqual(count, 1)
            metadata = json.loads(
                (stage_dir / "rbi_docs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                metadata[0]["metadata"]["category"],
                "notification_or_circular",
            )
            self.assertEqual(
                (active_index.read_bytes(), active_metadata.read_text(encoding="utf-8")),
                before_active,
            )


if __name__ == "__main__":
    unittest.main()
