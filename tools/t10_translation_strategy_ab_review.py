#!/usr/bin/env python3
"""Frozen NEW paragraph-only ML Kit strategy A/B, not the original T10 CP4 gate.

init RAW SESSION: validate all 60 matched two-strategy pairs, create a readable
offline browser review with no prefilled human judgments, and pin raw/fixture SHA.
report RAW SESSION REVIEW.csv [--json PATH]: require all 120 reviewed outcomes,
protect original outputs, calculate paired results. Never promotes CP4.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

FIXTURE = (Path(__file__).resolve().parent.parent /
           "engine/translation/src/androidTest/assets/t10_translation_strategy_ab_fixtures.json")
ORIGINAL_FIXTURE = (Path(__file__).resolve().parent.parent /
                    "engine/translation/src/androidTest/assets/t10_translation_fixtures.json")
RAW_COLUMNS = (
    "sample", "source_language", "target_language", "source_text", "strategy",
    "translation", "latency_ms", "error", "call_count", "sequence", "battery_c",
)
REVIEW_COLUMNS = (*RAW_COLUMNS, "status", "notes")
STATUS = {"ACCEPT", "MAJOR_MEANING_ERROR", "NEGATION_ERROR", "NUMBER_OR_NAME_ERROR"}
STRATEGIES = ("whole", "linewise")
META_NAME = "session.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_data(path: Path = FIXTURE, original: Path = ORIGINAL_FIXTURE) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = data.get("samples")
    if data.get("version") != 1 or not isinstance(rows, list) or len(rows) != 60:
        raise ValueError("Unexpected new A/B fixture version or sample count")
    old = json.loads(original.read_text(encoding="utf-8-sig"))
    old_sources = {row["text"].strip().casefold() for row in old["samples"]}
    if len(old_sources) != 60:
        raise ValueError("Original frozen CP4 input fixture invalid")
    ids = set()
    language_counts = Counter()
    for i, row in enumerate(rows):
        lang, sample, source = row["language"], row["id"], row["text"]
        expected = f"{lang}-ab-{i % 30 + 1:02d}"
        if sample != expected or sample in ids or lang not in ("id", "en"):
            raise ValueError("Unexpected A/B fixture id/order/language: " + sample)
        if (i < 30) != (lang == "id"):
            raise ValueError("Fixture directions not in fixed 30+30 order")
        ids.add(sample)
        language_counts[lang] += 1
        parts = source.split("\n")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise ValueError("Fixture sample must have two nonblank newline sentences: " + sample)
        if source.strip().casefold() in old_sources:
            raise ValueError("New paragraph overlaps frozen original benchmark: " + sample)
        if row.get("risk_tag", "").strip() == "":
            raise ValueError("Missing predeclared risk tag: " + sample)
    if language_counts != {"id": 30, "en": 30}:
        raise ValueError("Expected exactly 30 samples for each language")
    return rows


def read_csv(path: Path, expected_columns: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(expected_columns):
            raise ValueError("Invalid CSV columns/order for " + str(path))
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("CSV has malformed or extra columns")
    return rows


def validate_raw(raw: Path, fixture: Path = FIXTURE, original: Path = ORIGINAL_FIXTURE
                 ) -> list[dict[str, str]]:
    samples = fixture_data(fixture, original)
    rows = read_csv(raw, RAW_COLUMNS)
    if len(rows) != 120:
        raise ValueError(f"Expected 120 raw rows, found {len(rows)}; no incomplete A/B pairs")
    for i, sample in enumerate(samples):
        order = STRATEGIES if i % 2 == 0 else tuple(reversed(STRATEGIES))
        for j, strategy in enumerate(order):
            n = 2 * i + j
            r = rows[n]
            src = sample["language"]
            target = "en" if src == "id" else "id"
            if (r["sample"], r["source_language"], r["target_language"],
                r["source_text"], r["strategy"]) != (
                sample["id"], src, target, sample["text"], strategy
            ):
                raise ValueError(f"Missing/tampered A/B pair or order near row {n + 1}")
            if r["call_count"] != ("1" if strategy == "whole" else "2"):
                raise ValueError("Strategy call count not preserved for " + r["sample"])
            if r["sequence"] != str(n + 1):
                raise ValueError("Sequence order incorrect: " + r["sample"])
            try:
                elapsed = float(r["latency_ms"])
                battery = float(r["battery_c"])
            except ValueError as exc:
                raise ValueError("Non-numeric timing/battery: " + r["sample"]) from exc
            if not math.isfinite(elapsed) or elapsed <= 0:
                raise ValueError("Invalid latency: " + r["sample"])
            if not math.isfinite(battery) or not (0.0 < battery < 43.0):
                raise ValueError("Missing/unsafe battery-temperature sample: " + r["sample"])
    return rows


def emit_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def html_page(rows: list[dict[str, str]], fixture_rows: list[dict]) -> str:
    # JSON is embedded as literal data; escape '<' to prevent any model output
    # from injecting closing script tags. Always show model text via textContent.
    input_json = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    tags_json = json.dumps({r["id"]: r["risk_tag"] for r in fixture_rows},
                           ensure_ascii=False).replace("<", "\\u003c")
    template = r"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SubLoka T10 — 60 Paragraf A/B Offline</title>
<style>
:root{font-family:system-ui,Segoe UI,sans-serif;color:#172331;background:#f3f5f8}
body{max-width:1100px;margin:auto;padding:20px;line-height:1.55}
header,.pair{background:white;padding:20px;border:1px solid #dbe2e8;border-radius:15px;margin:0 0 18px}
h1{font-size:1.5rem;margin:0}h2{font-size:1.15rem;margin:0 0 5px}
.sub{color:#45566b}.meta{font-size:.88rem;color:#536376}
.source{white-space:pre-wrap;background:#edf4fc;padding:13px;border-radius:10px;margin:12px 0}
.outputs{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.output{background:#f6f8fc;padding:14px;border:1px solid #e0e6ee;border-radius:11px}
.hyp{white-space:pre-wrap;min-height:48px}
label{display:block;font-size:.9rem;font-weight:600;margin-top:10px}
select,textarea,input{font:inherit;width:100%;box-sizing:border-box;padding:9px;border:1px solid #b9c5d5;border-radius:7px;background:white}
textarea{min-height:62px}button{font:inherit;padding:9px 13px;border:1px solid #aaa;border-radius:8px;background:#1c496e;color:white;cursor:pointer}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0}
#count{font-weight:700}small{color:#526478}
@media(max-width:740px){body{padding:10px}.outputs{grid-template-columns:1fr}}
</style></head><body>
<header><h1>SubLoka T10 — Perbandingan Terjemahan Offline</h1>
<p>Ini 60 paragraf baru, <b>bukan</b> benchmark CP4 lama. Setiap paragraf memiliki dua terjemahan ML Kit. Nilai makna penuh kedua versi secara terpisah; jangan memilih hanya karena lebih lancar secara tata bahasa.</p>
<p class="sub">Kartu menyebut Output 1 / Output 2, bukan nama strategi. Simpan kemajuan menggunakan Ekspor CSV; data tidak dikirim melalui internet. Tidak ada status yang diisi otomatis. Jika dibuka kembali, gunakan Impor CSV hasil simpanan sebelumnya.</p>
<div class="toolbar"><span id="count">0/120 dinilai</span><button id="export" type="button">Ekspor review CSV</button>
<label style="margin:0">Impor CSV sebelumnya <input type="file" accept=".csv,text/csv" id="import"></label></div>
<small>Tiap penolakan membutuhkan catatan konkret. Status tersedia: ACCEPT, MAJOR_MEANING_ERROR, NEGATION_ERROR, NUMBER_OR_NAME_ERROR.</small>
<p id="message" role="status"></p></header>
<main id="pairs"></main>
<script>
const original=__RAW__;
const tags=__TAGS__;
const columns=__COLUMNS__;
const state=new Map();
const choices=["","ACCEPT","MAJOR_MEANING_ERROR","NEGATION_ERROR","NUMBER_OR_NAME_ERROR"];
const root=document.getElementById("pairs");
function node(tag,cls,content){const n=document.createElement(tag);if(cls)n.className=cls;if(content!==undefined)n.textContent=content;return n;}
function count(){const good=[...state.values()].filter(x=>x.status).length;document.getElementById("count").textContent=good+"/120 dinilai";}
function render(){
root.replaceChildren();
for(let i=0;i<60;i++){
  const pair=original.slice(i*2,i*2+2), article=node("article","pair"), title=node("h2","",pair[0].sample);
  article.append(title,node("div","meta","Kategori: "+(tags[pair[0].sample]||"")+
     " • "+(pair[0].source_language==="id"?"Indonesia → Inggris":"Inggris → Indonesia")));
  article.append(node("div","source",pair[0].source_text));
  const outputs=node("div","outputs");
  for(let j=0;j<2;j++){
    const row=pair[j], key=row.sample+"|"+row.strategy, current=state.get(key)||{status:"",notes:""};
    const cell=node("section","output");
    cell.append(node("strong","",j===0?"Output 1":"Output 2"),node("div","hyp",row.translation||"(hasil kosong)"));
    cell.append(node("small","",row.latency_ms+" ms; "+row.call_count+" panggilan model; error="+(row.error||"none")));
    const label=node("label","","Keputusan makna"), select=node("select");
    for(const choice of choices){const option=document.createElement("option");option.value=choice;
      option.textContent=choice||"— belum dinilai —";select.append(option);}
    select.value=current.status;
    const noteslabel=node("label","","Alasan / catatan"), notes=node("textarea");
    notes.value=current.notes;notes.placeholder="Wajib bila status bukan ACCEPT";
    select.addEventListener("change",()=>{state.set(key,{status:select.value,notes:notes.value});count();});
    notes.addEventListener("input",()=>{state.set(key,{status:select.value,notes:notes.value});count();});
    label.append(select);noteslabel.append(notes);cell.append(label,noteslabel);outputs.append(cell);
  }
  article.append(outputs);root.append(article);
}count();}
function escapeCSV(s){return '"'+String(s??"").replaceAll('"','""')+'"';}
function exportCSV(){
  const rows=[columns.join(",")];
  for(const row of original){
    const st=state.get(row.sample+"|"+row.strategy)||{status:"",notes:""};
    rows.push(columns.map(k=>escapeCSV(k==="status"?st.status:k==="notes"?st.notes:row[k])).join(","));
  }
  const file=new Blob(["\uFEFF"+rows.join("\r\n")+"\r\n"],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(file),a=document.createElement("a");a.href=url;a.download="translation-strategy-ab-review.csv";
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
  document.getElementById("message").textContent="CSV disimpan. Untuk resume, impor CSV ini saat membuka laporan kembali.";
}
function parseCSV(s){
  if(s.charCodeAt(0)===0xFEFF)s=s.slice(1);
  const table=[];let row=[],field="",quoted=false;
  for(let i=0;i<s.length;i++){const c=s[i];
    if(quoted){if(c==='"'&&s[i+1]==='"'){field+='"';i++;}else if(c==='"'){quoted=false;}else{field+=c;}}
    else if(c==='"'){quoted=true;}
    else if(c===","){row.push(field);field="";}
    else if(c==="\n"){row.push(field);if(row.length>1)table.push(row);row=[];field="";}
    else if(c!=="\r"){field+=c;}
  }
  if(quoted)throw Error("CSV quote belum ditutup");
  if(field||row.length){row.push(field);table.push(row);}
  return table;
}
async function importCSV(file){
  const parsed=parseCSV(await file.text());
  if(parsed.length!==121||parsed[0].join("|")!==columns.join("|"))throw Error("CSV bukan review A/B 120 baris");
  const copy=new Map();
  for(let i=1;i<parsed.length;i++){
    const obj=Object.fromEntries(columns.map((k,j)=>[k,parsed[i][j]]));
    const orig=original[i-1];
    if(parsed[i].length!==columns.length||columns.slice(0,-2).some(k=>obj[k]!==orig[k]))throw Error("Data asli diubah pada baris "+i);
    const key=obj.sample+"|"+obj.strategy;
    if(copy.has(key)||!choices.includes(obj.status))throw Error("Keputusan/ID tidak valid "+key);
    copy.set(key,{status:obj.status,notes:obj.notes});
  }
  state.clear();for(const [k,v] of copy)state.set(k,v);
  render();document.getElementById("message").textContent="Review dipulihkan. Silakan lanjutkan.";
}
document.getElementById("export").addEventListener("click",exportCSV);
document.getElementById("import").addEventListener("change",async e=>{
try{if(e.target.files[0])await importCSV(e.target.files[0]);}catch(err){document.getElementById("message").textContent="Gagal impor: "+err.message;}
});
render();
</script></body></html>"""
    return (template.replace("__RAW__", input_json)
            .replace("__TAGS__", tags_json)
            .replace("__COLUMNS__", json.dumps(REVIEW_COLUMNS)))


def init(raw: Path, session: Path, fixture: Path = FIXTURE, original: Path = ORIGINAL_FIXTURE) -> dict:
    rows = validate_raw(raw, fixture, original)
    if session.exists():
        raise FileExistsError("Session folder exists; refuse overwrite: " + str(session))
    fixture_rows = fixture_data(fixture, original)
    meta = {
        "version": 1,
        "evidence": "T10 new-paragraph offline ML Kit sentence-strategy A/B, NOT CP4",
        "raw_sha256": sha(raw),
        "fixture_sha256": sha(fixture),
        "original_fixture_sha256": sha(original),
        "raw_rows": len(rows),
        "paired_samples": len(fixture_rows),
        "order": "Alternating AB/BA within each source; all 60 samples are mandatory",
        "strategy_description": {
            "whole": "Original two-sentence paragraph in one ML Kit translation call",
            "linewise": "Two isolated ML Kit translation calls; join results with a space",
        },
        "predeclared_candidate_thresholds": {
            "min_candidate_accepted_per_direction": 27,
            "min_net_additional_accepted_per_direction": 3,
            "no_new_negation_or_number_name_errors": True,
            "max_candidate_p95_to_control_p95_ratio": 2.5,
            "requires_new_independent_unseen_confirmation_before_promotion": True,
        },
        "human_decisions": "Blank until explicitly entered; no AI review inferred",
        "cp4": "BLOCKED",
    }
    session.mkdir(parents=True)
    (session / META_NAME).write_text(json.dumps(meta, indent=2, ensure_ascii=False)+"\n",
                                    encoding="utf-8")
    emit_csv(session/"review-blank.csv", REVIEW_COLUMNS,
             [{**row, "status": "", "notes": ""} for row in rows])
    (session/"review.html").write_text(html_page(rows, fixture_rows), encoding="utf-8")
    print("Created browser review:", session/"review.html")
    print("Raw SHA256:", meta["raw_sha256"])
    print("Review 120 outputs for 60 paired NEW paragraphs; save CSV from browser.")
    print("CP4 gate unchanged; no physical-device result or human ratings assumed.")
    return meta


def analyze(raw: Path, session: Path, review: Path, fixture: Path = FIXTURE,
            original: Path = ORIGINAL_FIXTURE) -> dict:
    meta = json.loads((session/META_NAME).read_text(encoding="utf-8"))
    rows = validate_raw(raw, fixture, original)
    if (meta.get("version") != 1 or meta.get("raw_sha256") != sha(raw) or
        meta.get("fixture_sha256") != sha(fixture) or
        meta.get("original_fixture_sha256") != sha(original) or
        meta.get("paired_samples") != 60 or meta.get("raw_rows") != 120):
        raise ValueError("Session identity or original raw/fixture hash changed")
    rated = read_csv(review, REVIEW_COLUMNS)
    if len(rated) != 120:
        raise ValueError("Review must contain 120 original rows")
    for i, (old, new) in enumerate(zip(rows, rated)):
        if any(old[key] != new[key] for key in RAW_COLUMNS):
            raise ValueError(f"Reviewer changed raw output/identity at row {i+1}")
        if new["status"] not in STATUS:
            raise ValueError("Missing/invalid human review at " + old["sample"] + "/" + old["strategy"])
        if new["status"] != "ACCEPT" and not new["notes"].strip():
            raise ValueError("Rejection must have concrete explanation at " + old["sample"])
        if (new["error"].strip() or not new["translation"].strip()) and new["status"] == "ACCEPT":
            raise ValueError("Cannot ACCEPT engine error/empty translation at " + old["sample"])
    directions = {}
    candidate_promising = True
    for src,target in (("id","en"),("en","id")):
        specific = [r for r in rated if r["source_language"] == src]
        by_sample = {}
        for row in specific:
            by_sample.setdefault(row["sample"], {})[row["strategy"]] = row
        totals = {}
        for strategy in STRATEGIES:
            subset = [r for r in specific if r["strategy"] == strategy]
            times = sorted(float(r["latency_ms"]) for r in subset)
            totals[strategy] = {
                "reviewed": len(subset),
                "accepted": sum(r["status"] == "ACCEPT" for r in subset),
                "major_meaning_errors": sum(r["status"] == "MAJOR_MEANING_ERROR" for r in subset),
                "negation_errors": sum(r["status"] == "NEGATION_ERROR" for r in subset),
                "number_or_name_errors": sum(r["status"] == "NUMBER_OR_NAME_ERROR" for r in subset),
                "engine_or_empty_outputs": [r["sample"] for r in subset
                                            if r["error"].strip() or not r["translation"].strip()],
                "median_latency_ms": statistics.median(times),
                "p95_latency_ms": times[math.ceil(.95*len(times))-1],
            }
        wins = losses = 0
        critical_new = []
        for sample, pair in by_sample.items():
            w, l = pair["whole"], pair["linewise"]
            if l["status"] == "ACCEPT" and w["status"] != "ACCEPT":
                wins += 1
            if w["status"] == "ACCEPT" and l["status"] != "ACCEPT":
                losses += 1
            if l["status"] in ("NEGATION_ERROR","NUMBER_OR_NAME_ERROR") and (
                w["status"] != l["status"]
            ):
                critical_new.append(sample)
        control, candidate = totals["whole"],totals["linewise"]
        ratio = candidate["p95_latency_ms"]/control["p95_latency_ms"] if control["p95_latency_ms"] else math.inf
        evidence_promising = (
            candidate["accepted"] >= 27 and
            candidate["accepted"] - control["accepted"] >= 3 and
            not critical_new and
            not candidate["engine_or_empty_outputs"] and
            ratio <= 2.5
        )
        candidate_promising = candidate_promising and evidence_promising
        directions[f"{src}->{target}"] = {
            "whole": control,
            "linewise": candidate,
            "paired_wins_candidate": wins,
            "paired_losses_candidate": losses,
            "net_accepted_gain_candidate": candidate["accepted"]-control["accepted"],
            "new_material_negation_or_number_name_errors":critical_new,
            "candidate_to_control_p95_latency_ratio":ratio,
            "predeclared_diagnostic_threshold_met":evidence_promising,
        }
    return {
        "evidence_type":"COMPLETED_REVIEW_OF_NEW_TRANSLATION_STRATEGY_AB_NOT_CP4",
        "raw_sha256":sha(raw),
        "fixture_sha256":sha(fixture),
        "human_review_csv_sha256":sha(review),
        "sample_pairs":60,
        "variant_rows":120,
        "directions":directions,
        "overall":"CANDIDATE_PROMISING_REQUIRES_INDEPENDENT_FOLLOWUP" if candidate_promising
                  else "NO_BASIS_TO_PROMOTE_CANDIDATE",
        "reviewer_identity_independence":"Not verified by script",
        "offline_device_evidence":"PowerShell/ADB preflight required; not inferred from CSV",
        "original_cp4_fixture_or_outputs_changed":False,
        "cp4_status":"BLOCKED",
        "t11":"TODO",
    }


def report(raw: Path, session: Path, review: Path, target: Path | None = None,
           fixture: Path = FIXTURE, original: Path = ORIGINAL_FIXTURE) -> dict:
    result = analyze(raw, session, review, fixture, original)
    for direction, values in result["directions"].items():
        a, b = values["whole"], values["linewise"]
        print(f"{direction}: whole {a['accepted']}/30 vs linewise {b['accepted']}/30 "
              f"(candidate net {values['net_accepted_gain_candidate']:+d}); "
              f"paired wins/losses {values['paired_wins_candidate']}/{values['paired_losses_candidate']}; "
              f"p95 ratio {values['candidate_to_control_p95_latency_ratio']:.2f}; "
              f"diagnostic criteria {values['predeclared_diagnostic_threshold_met']}")
    print(result["overall"], "| CP4 BLOCKED | New source fixture is NOT the official gate.")
    if target is not None:
        if target.exists():
            raise FileExistsError("Refusing overwrite of report: "+str(target))
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    cmd=p.add_subparsers(dest="command",required=True)
    prep=cmd.add_parser("init")
    prep.add_argument("raw",type=Path)
    prep.add_argument("session",type=Path)
    done=cmd.add_parser("report")
    done.add_argument("raw",type=Path)
    done.add_argument("session",type=Path)
    done.add_argument("review",type=Path)
    done.add_argument("--json",type=Path,default=None)
    args=p.parse_args()
    try:
        if args.command=="init":
            init(args.raw,args.session)
        else:
            report(args.raw,args.session,args.review,args.json)
        return 0
    except (ValueError,FileNotFoundError,FileExistsError,KeyError,csv.Error,
            json.JSONDecodeError) as e:
        print("ERROR:",e,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
