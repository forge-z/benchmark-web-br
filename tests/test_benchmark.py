"""Dry-run, CSV schema, and deterministic grading. No network."""

from __future__ import annotations

import csv
import json
import os
import unittest
from pathlib import Path

from runners import fields
from runners.common import ROOT
from grade.grade import grade_records
from grade.score import bootstrap, net

DATA = ROOT / "datasets"
RESULT_KEYS = {
    "schema_version", "run_id", "prova", "tool", "item_id", "dry_run", "skipped",
    "skip_reason", "started_at", "finished_at", "latency_ms", "http_status", "error",
    "estimated_credits", "estimated_cost_usd", "calls", "output",
}


def read(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Datasets(unittest.TestCase):
    def test_counts_and_status(self):
        sites = read("sites_noticias.csv")
        queries = read("consultas_noticias.csv")
        urls = read("urls_leitura.csv")
        companies = read("empresas.csv")
        questions = read("perguntas_empresas.csv")
        self.assertEqual(len(sites), 25)
        self.assertEqual(len(queries), 40)
        self.assertEqual(len(urls), 60)
        self.assertEqual(len(companies), 30)
        self.assertEqual(len(questions), 10)
        self.assertTrue(all(row["gabarito_status"] == "verificado" for row in sites))
        self.assertTrue(all(row["http_status"] == "200" for row in sites))
        self.assertTrue(all(row["gabarito_status"] == "a revisar" for row in queries))
        news = [row for row in urls if row["tipo"] == "noticia"]
        pdfs = [row for row in urls if row["tipo"] == "pdf"]
        products = [row for row in urls if row["tipo"] == "produto"]
        self.assertEqual(len(news), 20)
        self.assertEqual(len(pdfs), 10)
        self.assertEqual(len(products), 30)
        self.assertEqual(sum(row["gabarito_status"] == "verificado" for row in products), 26)
        shopee = [row for row in products if row["veiculo"] == "Shopee"]
        self.assertEqual(len(shopee), 4)
        self.assertTrue(all(row["gabarito_status"] == "a revisar" for row in shopee))
        self.assertTrue(all(not row["titulo_esperado"] and not row["preco_esperado"] for row in shopee))
        self.assertTrue(all(row["titulo_esperado"] and row["data_esperada"] for row in news))
        self.assertEqual(sum(row["gabarito_status"] == "verificado" for row in companies), 29)
        self.assertEqual(sum(row["gabarito_status"] == "a revisar" for row in companies), 1)
        by_id = {row["id"]: row for row in companies}
        self.assertEqual(by_id["e02"]["cnpj"], "84.683.374/0003-00")
        self.assertEqual(by_id["e02"]["cidade"], "JOINVILLE")
        self.assertEqual(by_id["e02"]["uf"], "SC")
        self.assertTrue(by_id["e02"]["segmento"])
        self.assertEqual(by_id["e02"]["gabarito_status"], "verificado")
        self.assertEqual(by_id["e12"]["cnpj"], "56.720.428/0014-88")
        self.assertEqual(by_id["e13"]["cnpj"], "89.086.144/0011-98")
        self.assertEqual(by_id["e18"]["cidade"], "TIJUCAS")
        self.assertEqual(by_id["e18"]["uf"], "SC")
        self.assertEqual(by_id["e18"]["gabarito_status"], "verificado")
        self.assertEqual(by_id["e25"]["gabarito_status"], "a revisar")
        self.assertEqual(by_id["e25"]["cnpj"], "")
        for row in companies:
            if row["linkedin_empresa"]:
                self.assertIn("/company/", row["linkedin_empresa"])
                self.assertNotIn("/in/", row["linkedin_empresa"])

    def test_cnpj_and_privacy(self):
        blob = "\n".join((DATA / name).read_text(encoding="utf-8") for name in (
            "sites_noticias.csv", "consultas_noticias.csv", "urls_leitura.csv",
            "empresas.csv", "perguntas_empresas.csv",
        ))
        self.assertNotIn("@", blob)
        lowered = blob.lower()
        for banned in ("api_key", "bearer ", "sk-", "senha"):
            self.assertNotIn(banned, lowered)
        for row in read("empresas.csv"):
            if row["cnpj"]:
                self.assertTrue(fields.cnpj_valid(row["cnpj"]), row["id"])
                self.assertEqual(row["cnpj"], fields.format_cnpj(row["cnpj"]))

    def test_urls_are_absolute(self):
        for name, column in (("sites_noticias.csv", "url"), ("urls_leitura.csv", "url")):
            for row in read(name):
                self.assertTrue(row[column].startswith("https://"), row["id"])


class Fields(unittest.TestCase):
    def test_price(self):
        self.assertEqual(fields.canonical_price("por R$ 1.234,50 à vista"), "R$ 1.234,50")
        self.assertEqual(fields.canonical_price("R$ 49,98"), "R$ 49,98")
        self.assertEqual(fields.canonical_price("sem preço"), "")

    def test_cnpj_rejects_bad_digit(self):
        self.assertFalse(fields.cnpj_valid("84.429.695/0001-10"))
        self.assertTrue(fields.cnpj_valid("84.429.695/0001-11"))


class DryRun(unittest.TestCase):
    def test_runners_do_not_call_the_network(self):
        import runners.baseline as baseline
        import runners.context_dev as context_dev
        import runners.exa as exa
        import runners.firecrawl as firecrawl
        import runners.parallel as parallel
        import runners.tinyfish as tinyfish
        from runners import common

        def boom(*_args, **_kwargs):
            raise AssertionError("dry-run chamou a rede")

        original = common.request_json
        common.request_json = boom
        secret = "test-secret-should-not-appear"
        previous = {name: os.environ.get(name) for name in (
            "EXA_API_KEY", "PARALLEL_API_KEY", "TINYFISH_API_KEY",
            "FIRECRAWL_API_KEY", "CONTEXT_DEV_API_KEY",
        )}
        for name in previous:
            os.environ[name] = secret
        try:
            modules = (baseline, exa, parallel, tinyfish, firecrawl, context_dev)
            with self._tmpdir() as out:
                for module in modules:
                    for prova in ("noticias", "leitura", "empresas"):
                        code = module.main([
                            "--prova", prova, "--dry-run", "--limit", "1",
                            "--out", str(out), "--datasets", str(DATA),
                        ])
                        self.assertEqual(code, 0)
                files = list(Path(out).glob("*.jsonl"))
                self.assertGreaterEqual(len(files), 3)
                tools = set()
                for path in files:
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn(secret, text)
                    for line in text.splitlines():
                        record = json.loads(line)
                        self.assertTrue(RESULT_KEYS <= set(record))
                        self.assertTrue(record["dry_run"])
                        self.assertFalse(record["skipped"])
                        self.assertTrue(record["calls"])
                        tools.add(record["tool"])
                self.assertIn("parallel_task_core", tools)
                self.assertIn("baseline", tools)
        finally:
            common.request_json = original
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_missing_key_skips_without_network(self):
        import runners.exa as exa
        from runners import common

        def boom(*_args, **_kwargs):
            raise AssertionError("skip chamou a rede")

        original = common.request_json
        common.request_json = boom
        os.environ.pop("EXA_API_KEY", None)
        try:
            with self._tmpdir() as out:
                code = exa.main(["--prova", "noticias", "--limit", "1", "--out", str(out), "--datasets", str(DATA)])
                self.assertEqual(code, 0)
                record = json.loads(next(Path(out).glob("*.jsonl")).read_text().splitlines()[0])
                self.assertTrue(record["skipped"])
                self.assertIn("EXA_API_KEY", record["skip_reason"])
        finally:
            common.request_json = original

    def test_parallel_and_firecrawl_bodies(self):
        import runners.firecrawl as firecrawl
        import runners.parallel as parallel

        with self._tmpdir() as out:
            self.assertEqual(parallel.main([
                "--prova", "noticias", "--dry-run", "--limit", "1",
                "--out", str(out), "--datasets", str(DATA),
            ]), 0)
            self.assertEqual(parallel.main([
                "--prova", "empresas", "--dry-run", "--limit", "1",
                "--out", str(out), "--datasets", str(DATA),
            ]), 0)
            self.assertEqual(firecrawl.main([
                "--prova", "empresas", "--dry-run", "--limit", "1",
                "--out", str(out), "--datasets", str(DATA),
            ]), 0)
            news = json.loads(next(Path(out).glob("parallel__noticias__*.jsonl")).read_text().splitlines()[0])
            search = news["calls"][0]
            self.assertEqual(search["endpoint"], "https://api.parallel.ai/v1/search")
            self.assertEqual(search["request"]["max_chars_total"], 8000)
            self.assertNotIn("excerpts", search["request"])
            self.assertEqual(search["request"]["advanced_settings"]["max_results"], 10)
            task = json.loads(next(Path(out).glob("parallel_task_core__empresas__*.jsonl")).read_text().splitlines()[0])
            schema = task["calls"][0]["request"]["task_spec"]["output_schema"]
            self.assertEqual(schema["type"], "json")
            self.assertIn("cnpj", schema["json_schema"]["properties"])
            self.assertTrue(task["calls"][0]["endpoint"].endswith("/v1/tasks/runs"))
            company = json.loads(next(Path(out).glob("firecrawl__empresas__*.jsonl")).read_text().splitlines()[0])
            scrapes = [call for call in company["calls"] if call["call"] == "scrape_json"]
            self.assertEqual(len(scrapes), 3)
            self.assertTrue(all(call["endpoint"].endswith("/v2/scrape") for call in scrapes))
            self.assertTrue(all("/extract" not in call["endpoint"] for call in company["calls"]))
            fmt = scrapes[0]["request"]["formats"][0]
            self.assertEqual(fmt["type"], "json")
            self.assertIn("schema", fmt)
            self.assertIn("prompt", fmt)
            self.assertEqual(scrapes[0]["request"]["url"], "")

    def test_company_plan_does_not_carry_the_answer(self):
        import runners.exa as exa
        from runners.common import read_csv, task_text

        row = next(item for item in read_csv(DATA / "empresas.csv") if item["id"] == "e01")
        perguntas = read_csv(DATA / "perguntas_empresas.csv")
        ctx = {
            "prova": "empresas",
            "perguntas": perguntas,
            "window_start": __import__("datetime").datetime(2026, 11, 18, tzinfo=__import__("datetime").timezone.utc),
            "window_end": __import__("datetime").datetime(2026, 11, 18, 12, tzinfo=__import__("datetime").timezone.utc),
            "datasets": DATA,
        }
        body = json.dumps(exa.plan(row, ctx), ensure_ascii=False)
        self.assertNotIn(row["cnpj"], body)
        self.assertNotIn("84429695000111", body)
        self.assertIn("WEG", task_text(row["nome"], perguntas))

    def _tmpdir(self):
        import tempfile
        return tempfile.TemporaryDirectory()


class Sample(unittest.TestCase):
    def test_same_seed_same_csv(self):
        from grade.amostra import main

        with self._tmpdir() as out:
            first = Path(out) / "a.csv"
            second = Path(out) / "b.csv"
            self.assertEqual(main(["--out", str(first), "--n", "5", "--seed", "20261118", "--datasets", str(DATA)]), 0)
            self.assertEqual(main(["--out", str(second), "--n", "5", "--seed", "20261118", "--datasets", str(DATA)]), 0)
            self.assertEqual(first.read_text(encoding="utf-8"), second.read_text(encoding="utf-8"))
            other = Path(out) / "c.csv"
            main(["--out", str(other), "--n", "5", "--seed", "1", "--datasets", str(DATA)])
            self.assertNotEqual(first.read_text(encoding="utf-8"), other.read_text(encoding="utf-8"))
            header = first.read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("revisao_humana", header)
            self.assertEqual(len(first.read_text(encoding="utf-8").splitlines()), 6)

    def test_cells_sample_keeps_grades(self):
        from grade.amostra import main

        cells = [
            {"tool": "exa", "prova": "empresas", "item_id": "e01", "field": "cidade", "grade": "certo", "expected": "JARAGUA DO SUL", "answer": "Jaraguá do Sul"},
            {"tool": "exa", "prova": "empresas", "item_id": "e01", "field": "ruido", "grade": "metrica", "expected": "", "answer": "0"},
        ]
        with self._tmpdir() as out:
            path = Path(out) / "cells.jsonl"
            path.write_text("\n".join(json.dumps(cell) for cell in cells) + "\n", encoding="utf-8")
            dest = Path(out) / "amostra.csv"
            main(["--cells", str(path), "--out", str(dest), "--n", "10", "--seed", "3"])
            text = dest.read_text(encoding="utf-8")
            self.assertIn("e01", text)
            self.assertIn("certo", text)
            self.assertNotIn("metrica", text)

    def _tmpdir(self):
        import tempfile
        return tempfile.TemporaryDirectory()


class Grading(unittest.TestCase):
    def test_news_window_and_net(self):
        record = {
            "tool": "exa", "prova": "noticias", "item_id": "q01", "dry_run": False, "skipped": False,
            "started_at": "2026-11-18T12:00:00Z",
            "output": {"items": [
                {"url": "https://exemplo.br/a", "title": "A", "published_at": "2026-11-17T12:00:00Z", "snippet": ""},
                {"url": "https://exemplo.br/b", "title": "B", "published_at": "2026-11-01T00:00:00Z", "snippet": ""},
                {"url": "https://exemplo.br/c", "title": "C", "published_at": "", "snippet": ""},
            ]},
        }
        cells = grade_records([record], DATA)
        grades = [cell["grade"] for cell in cells if cell["grade"] != "metrica"]
        self.assertEqual(grades, ["certo", "errado", "branco"])
        self.assertEqual(net(cells), 0.0)
        dup = next(cell for cell in cells if cell["field"] == "duplicatas_de_url")
        self.assertEqual(dup["answer"], "0")

    def test_price_and_cnpj_cells(self):
        page = {
            "tool": "baseline", "prova": "leitura", "item_id": "l01", "dry_run": False, "skipped": False,
            "output": {"title": "Toyota anuncia produção da picape híbrida flex Corolla Deck e 1,7 mil empregos na nova fábrica em SP | Valor",
                       "published_at": "2026-11-18T15:24:58Z", "price_brl": "", "seller": "", "availability": ""},
        }
        cells = grade_records([page], DATA)
        self.assertTrue(any(cell["field"] == "titulo" and cell["grade"] == "certo" for cell in cells))
        self.assertTrue(any(cell["field"] == "data" and cell["grade"] == "certo" for cell in cells))
        company = {
            "tool": "parallel", "prova": "empresas", "item_id": "e01", "dry_run": False, "skipped": False,
            "output": {"answers": {
                "cnpj": {"value": "84.429.695/0001-10", "citations": []},
                "razao_social": {"value": "WEG SA", "citations": []},
                "cidade": {"value": "Jaraguá do Sul", "citations": []},
                "uf": {"value": "SC", "citations": []},
                "porte": {"value": "DEMAIS", "citations": []},
                "segmento": {"value": "Holdings de instituições não-financeiras", "citations": []},
                "site": {"value": "https://ri.weg.net/institucional", "citations": []},
                "linkedin_empresa": {"value": "", "citations": []},
                "cargo_decisor_comercial": {"value": "fulano@empresa.com", "citations": []},
                "noticia_recente": {"value": "", "citations": []},
            }},
        }
        cells = grade_records([company], DATA)
        by_field = {cell["field"]: cell["grade"] for cell in cells}
        self.assertEqual(by_field["cnpj"], "errado")
        self.assertEqual(by_field["razao_social"], "certo")
        self.assertEqual(by_field["cidade"], "certo")
        self.assertEqual(by_field["site"], "certo")
        self.assertEqual(by_field["cargo_decisor_comercial"], "errado")
        self.assertNotIn("noticia_recente", by_field)
        filial = {
            "tool": "parallel", "prova": "empresas", "item_id": "e02", "dry_run": False, "skipped": False,
            "output": {"answers": {"cnpj": {"value": "84.683.374/0001-49", "citations": []}}},
        }
        filial_cells = {cell["field"]: cell["grade"] for cell in grade_records([filial], DATA)}
        self.assertEqual(filial_cells["cnpj"], "errado")
        self.assertTrue(fields.cnpj_valid("84.683.374/0001-49"))

    def test_noise_ratio_sees_a_menu(self):
        from grade.grade import noise_ratio

        menu = "\n".join(["Menu", "Home", "Contato", "https://exemplo.br/a", "- Loja"])
        prose = "\n".join([
            "A Toyota confirmou a produção da picape em Sorocaba nesta quarta-feira.",
            "A nota da montadora fala em empregos na nova fábrica.",
            "O texto segue por vários parágrafos sem lista de navegação.",
            "Não há preço nesta matéria de economia industrial.",
            "O parágrafo final repete a data de publicação já conferida.",
        ])
        self.assertGreater(noise_ratio(menu), 0.5)
        self.assertEqual(noise_ratio(prose), 0.0)

    def test_bootstrap_interval_contains_point_when_one_item(self):
        cells = [{"tool": "baseline", "item_id": "only", "grade": "certo"}]
        low, high = bootstrap(cells, resamples=50, seed=1)
        self.assertEqual(low, high)
        self.assertEqual(low, net(cells))


if __name__ == "__main__":
    unittest.main()
