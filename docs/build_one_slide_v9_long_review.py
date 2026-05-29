from __future__ import annotations

import copy
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASE = DOCS / "SecondOpinion_one_slide_v8_middle_flow.pptx"
OUT = DOCS / "SecondOpinion_one_slide_v9_long_review.pptx"
FULL_IMG = DOCS / "review_scoring_snapshot_yVdQ7kKCcl.png"
ZOOM_IMG = DOCS / "review_scoring_snapshot_yVdQ7kKCcl_zoom.png"

EMU = 914400
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

ET.register_namespace("p", P_NS)
ET.register_namespace("a", A_NS)
ET.register_namespace("r", R_NS)


def q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def inches(value: float) -> str:
    return str(int(round(value * EMU)))


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


FONT_REG = font("arial.ttf", 24)
FONT_BOLD = font("arialbd.ttf", 28)
FONT_BIG = font("arialbd.ttf", 58)
FONT_SMALL = font("arial.ttf", 20)
FONT_TINY = font("arial.ttf", 16)


def round_rect(draw: ImageDraw.ImageDraw, box, fill, outline="#d8dee4", width=3, radius=24):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def pill(draw: ImageDraw.ImageDraw, xy, text, fill, color="white", pad_x=16, pad_y=7):
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=FONT_TINY)
    w = bbox[2] - bbox[0] + pad_x * 2
    h = bbox[3] - bbox[1] + pad_y * 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=fill)
    draw.text((x + pad_x, y + pad_y - 1), text, font=FONT_TINY, fill=color)
    return w


def multiline(draw, xy, text, font_obj, fill="#111827", spacing=6, max_width=420):
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font_obj)[2] <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)

    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += font_obj.size + spacing
    return y


def make_full_scorecard() -> None:
    img = Image.new("RGB", (1180, 1260), "#f8fafc")
    draw = ImageDraw.Draw(img)

    round_rect(draw, (40, 40, 1140, 1220), "#ffffff", "#d7dee8", 4, 34)
    draw.text((80, 78), "SecondOpinion Review Audit", font=font("arialbd.ttf", 42), fill="#111827")
    draw.text((82, 130), "TabR review yVdQ7kKCcl  |  rating: 3  |  ICLR 2024 OpenReview", font=FONT_SMALL, fill="#475569")

    draw.rounded_rectangle((940, 72, 1088, 220), radius=20, fill="#c81e1e")
    draw.text((982, 86), "63", font=FONT_BIG, fill="white")
    draw.text((970, 156), "Review Quality", font=FONT_TINY, fill="white")
    draw.text((1004, 180), "Score", font=FONT_TINY, fill="white")

    draw.text((80, 210), "Review-level flags", font=FONT_BOLD, fill="#111827")
    x = 80
    for text, fill in [
        ("requires human expert check", "#d97706"),
        ("unverified quoted evidence", "#f97316"),
        ("vague criticism", "#ef4444"),
    ]:
        x += pill(draw, (x, 255), text, fill) + 14

    excerpt = (
        "Long review excerpt: module-design motivations are unclear; asks why L2 distance beats dot product, "
        "why T uses LinearWithoutBias, whether modules remain robust when dataset characteristics change, and "
        "whether middle-sized datasets are enough to justify the comparison."
    )
    round_rect(draw, (80, 320, 1100, 455), "#f9fafb", "#d8dee4", 3, 20)
    draw.text((105, 345), "Reviewer wrote", font=FONT_BOLD, fill="#111827")
    multiline(draw, (105, 386), excerpt, FONT_SMALL, "#111827", max_width=950)

    claims = [
        ("Claim 1", "L2 vs dot product rationale", "mixed", "partially supported", "low"),
        ("Claim 2", "LinearWithoutBias design choice", "mixed", "partially supported", "low"),
        ("Claim 3", "Robustness under dataset shifts", "agree", "supported", "medium"),
        ("Claim 4", "Large-scale evaluation / efficiency", "agree", "supported", "medium"),
        ("Claim 5", "Missing SOTA + feature sensitivity", "mixed", "partially supported", "low"),
        ("Claim 6", "Typo in continuous features", "strongly agree", "supported", "low"),
    ]

    colors = {
        "supported": "#047857",
        "partially supported": "#d97706",
    }
    for idx, (label, title, stance, verdict, conf) in enumerate(claims):
        col = idx % 2
        row = idx // 2
        left = 80 + col * 520
        top = 500 + row * 205
        outline = "#0f766e" if label == "Claim 3" else "#d8dee4"
        round_rect(draw, (left, top, left + 485, top + 165), "#ffffff", outline, 4, 20)
        draw.text((left + 24, top + 22), label, font=FONT_BOLD, fill="#0f766e" if label == "Claim 3" else "#111827")
        pill(draw, (left + 315, top + 20), verdict, colors[verdict], pad_x=12, pad_y=6)
        multiline(draw, (left + 24, top + 68), title, font("arialbd.ttf", 22), "#111827", max_width=430)
        draw.text((left + 24, top + 122), f"stance: {stance}   confidence: {conf}", font=FONT_TINY, fill="#475569")

    img.save(FULL_IMG)


def make_zoom_scorecard() -> None:
    img = Image.new("RGB", (900, 540), "#f8fafc")
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((26, 72, 190, 235), radius=22, fill="#c81e1e")
    draw.text((79, 90), "63", font=FONT_BIG, fill="white")
    draw.text((61, 165), "Review Quality", font=FONT_TINY, fill="white")
    draw.text((94, 190), "Score", font=FONT_TINY, fill="white")

    round_rect(draw, (225, 62, 862, 470), "#ffffff", "#0f766e", 5, 24)
    draw.text((255, 92), "Claim 3", font=FONT_BOLD, fill="#0f766e")
    pill(draw, (675, 90), "supported", "#047857", pad_x=14, pad_y=7)
    draw.text((255, 142), "Robustness under dataset shifts", font=font("arialbd.ttf", 29), fill="#111827")
    draw.text((255, 185), "verdict: supported | confidence: medium | support: 60", font=FONT_SMALL, fill="#0f766e")

    evidence = (
        "Evidence: author response discusses benchmark and dataset sizes, plus extended results. "
        "This supports the reviewer concern that middle-sized datasets alone do not fully establish robustness."
    )
    y = multiline(draw, (255, 230), evidence, FONT_SMALL, "#111827", spacing=7, max_width=560)
    draw.text((255, y + 10), "Guidance:", font=font("arialbd.ttf", 22), fill="#111827")
    multiline(
        draw,
        (255, y + 42),
        "Add a compact robustness table across dataset scales and distributions; report training time and memory.",
        FONT_SMALL,
        "#111827",
        spacing=7,
        max_width=560,
    )

    draw.ellipse((730, 14, 815, 99), outline="#0f766e", width=8)
    draw.line((795, 82, 872, 154), fill="#0f766e", width=8)
    img.save(ZOOM_IMG)


def set_xfrm(shape: ET.Element, x: float, y: float, w: float, h: float) -> None:
    xfrm = shape.find(f".//{q(A_NS, 'xfrm')}")
    if xfrm is None:
        return
    off = xfrm.find(q(A_NS, "off"))
    ext = xfrm.find(q(A_NS, "ext"))
    if off is not None:
        off.set("x", inches(x))
        off.set("y", inches(y))
    if ext is not None:
        ext.set("cx", inches(w))
        ext.set("cy", inches(h))


def make_run(text: str, size: int, bold: bool, color: str) -> ET.Element:
    run = ET.Element(q(A_NS, "r"))
    rpr = ET.SubElement(run, q(A_NS, "rPr"), {"sz": str(size), "b": "1" if bold else "0", "i": "0"})
    solid = ET.SubElement(rpr, q(A_NS, "solidFill"))
    ET.SubElement(solid, q(A_NS, "srgbClr"), {"val": color})
    ET.SubElement(rpr, q(A_NS, "latin"), {"typeface": "Aptos"})
    t = ET.SubElement(run, q(A_NS, "t"))
    t.text = text
    return run


def set_text(shape: ET.Element, paragraphs: list[dict]) -> None:
    tx = shape.find(q(P_NS, "txBody"))
    if tx is None:
        tx = ET.SubElement(shape, q(P_NS, "txBody"))
    for child in list(tx):
        tx.remove(child)
    ET.SubElement(tx, q(A_NS, "bodyPr"), {"rtlCol": "0", "anchor": "t", "tIns": "50292", "bIns": "50292"})
    ET.SubElement(tx, q(A_NS, "lstStyle"))
    for spec in paragraphs:
        p = ET.SubElement(tx, q(A_NS, "p"))
        attrs = {}
        if spec.get("align"):
            attrs["algn"] = spec["align"]
        ppr = ET.SubElement(p, q(A_NS, "pPr"), attrs)
        spc = ET.SubElement(ppr, q(A_NS, "spcAft"))
        ET.SubElement(spc, q(A_NS, "spcPts"), {"val": str(spec.get("after", 45))})
        p.append(make_run(spec["text"], spec.get("size", 760), spec.get("bold", False), spec.get("color", "111827")))


def block(title: str, lines: list[str], title_color: str, body_size: int = 690) -> list[dict]:
    out = [{"text": title, "size": 960, "bold": True, "color": title_color, "align": "ctr", "after": 40}]
    out.extend({"text": line, "size": body_size, "color": "111827", "after": 26} for line in lines)
    return out


def set_badge(shape: ET.Element, text: str) -> None:
    set_text(shape, [{"text": text, "size": 515, "bold": True, "color": "FFFFFF", "align": "ctr", "after": 0}])


def shape_id(shape: ET.Element) -> str | None:
    c_nv = shape.find(f".//{q(P_NS, 'cNvPr')}")
    return c_nv.get("id") if c_nv is not None else None


def replace_slide_xml(slide_xml: bytes) -> bytes:
    root = ET.fromstring(slide_xml)
    sp_tree = root.find(f".//{q(P_NS, 'spTree')}")
    shapes = {shape_id(s): s for s in list(sp_tree) if shape_id(s)}

    set_xfrm(shapes["61"], 4.73, 0.92, 4.00, 0.34)
    set_text(shapes["61"], [{"text": "2. Audit flow on a longer review", "size": 1720, "bold": True, "color": "00796B", "after": 0}])
    set_xfrm(shapes["62"], 4.74, 1.28, 3.92, 0.18)
    set_text(shapes["62"], [{"text": "Example: TabR review yVdQ7kKCcl (rating 3)", "size": 660, "color": "475569", "after": 0}])

    set_xfrm(shapes["63"], 4.74, 1.51, 3.96, 1.43)
    set_text(
        shapes["63"],
        block(
            "Reviewer wrote",
            [
                'Weakness excerpt: "module designs are not entirely clear"; asks why L2 beats dot product and why T uses LinearWithoutBias.',
                "Also questions robustness when dataset characteristics change and whether middle-sized datasets are enough.",
                "Question: is L2 sensitive to uninformative features?",
            ],
            "111827",
            640,
        ),
    )
    set_xfrm(shapes["64"], 7.42, 1.60, 1.10, 0.20)
    set_badge(shapes["64"], "INPUT")
    set_xfrm(shapes["65"], 6.58, 2.97, 0.28, 0.14)
    set_text(shapes["65"], [{"text": "↓", "size": 880, "bold": True, "color": "64748B", "align": "ctr", "after": 0}])

    set_xfrm(shapes["66"], 4.74, 3.15, 3.96, 0.78)
    set_text(
        shapes["66"],
        block(
            "System extracts review points",
            [
                "C1 L2 vs dot product | C2 LinearWithoutBias",
                "C3 robustness shifts | C4 large-scale efficiency",
                "C5 missing SOTA + feature sensitivity | C6 typo",
            ],
            "00796B",
            620,
        ),
    )
    set_xfrm(shapes["67"], 7.42, 3.20, 1.10, 0.20)
    set_badge(shapes["67"], "LLM: gpt-5-nano")
    set_xfrm(shapes["68"], 6.58, 3.95, 0.28, 0.14)
    set_text(shapes["68"], [{"text": "↓", "size": 880, "bold": True, "color": "64748B", "align": "ctr", "after": 0}])

    set_xfrm(shapes["69"], 4.74, 4.12, 3.96, 0.72)
    set_text(
        shapes["69"],
        block(
            "Evidence found",
            [
                "Search paper PDF chunks + appendix + author response",
                "Matches: benchmark/data-size response; L2 robustness response; extended tables",
            ],
            "006AA8",
            620,
        ),
    )
    set_xfrm(shapes["70"], 7.42, 4.17, 1.10, 0.20)
    set_badge(shapes["70"], "LOCAL")
    set_xfrm(shapes["71"], 6.58, 4.84, 0.28, 0.14)
    set_text(shapes["71"], [{"text": "↓", "size": 880, "bold": True, "color": "64748B", "align": "ctr", "after": 0}])

    set_xfrm(shapes["72"], 4.74, 5.02, 3.96, 0.82)
    set_text(
        shapes["72"],
        block(
            "SecondOpinion judges claims",
            [
                "C3: agree / supported / medium confidence",
                "C1-C2: mixed / partially supported / low",
                "Guidance: add theory + ablation + large-scale robustness table",
            ],
            "B45309",
            610,
        ),
    )
    set_xfrm(shapes["73"], 7.42, 5.08, 1.10, 0.20)
    set_badge(shapes["73"], "LLM: gpt-5-nano")
    set_xfrm(shapes["74"], 6.58, 5.86, 0.28, 0.14)
    set_text(shapes["74"], [{"text": "↓", "size": 880, "bold": True, "color": "64748B", "align": "ctr", "after": 0}])

    set_xfrm(shapes["75"], 4.74, 6.05, 3.96, 0.57)
    set_text(
        shapes["75"],
        block(
            "Reliability + report",
            ["Flag expert-check + weak quote evidence; output RQS 63 + HTML report"],
            "B91C1C",
            620,
        ),
    )
    set_xfrm(shapes["76"], 7.42, 6.12, 1.10, 0.20)
    set_badge(shapes["76"], "LOCAL")
    set_xfrm(shapes["77"], 4.74, 6.78, 3.96, 0.23)
    set_text(
        shapes["77"],
        [{"text": "Two LLM calls; retrieval, reliability checks, and reporting stay local.", "size": 585, "bold": True, "color": "FFFFFF", "align": "ctr", "after": 0}],
    )

    set_text(
        shapes["53"],
        [{"text": "Same TabR review: full scorecard + zoomed claim", "size": 700, "color": "475569", "after": 0}],
    )
    set_text(
        shapes["56"],
        [
            {"text": "RQS", "size": 1000, "bold": True, "color": "C81E1E", "align": "ctr", "after": 35},
            {"text": "63", "size": 2450, "bold": True, "color": "C81E1E", "align": "ctr", "after": 70},
            {"text": "Claim 3", "size": 850, "bold": True, "color": "00796B", "align": "ctr", "after": 20},
            {"text": "supported", "size": 850, "bold": True, "color": "00796B", "align": "ctr", "after": 20},
            {"text": "medium confidence", "size": 650, "color": "475569", "align": "ctr", "after": 0},
        ],
    )
    set_text(
        shapes["60"],
        [{"text": "Demo report: reports/mvp_demo_three_papers.html  |  Review: yVdQ7kKCcl", "size": 545, "bold": True, "color": "FFFFFF", "align": "ctr", "after": 0}],
    )

    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def write_pptx() -> None:
    make_full_scorecard()
    make_zoom_scorecard()
    new_slide = None
    with zipfile.ZipFile(BASE, "r") as src:
        new_slide = replace_slide_xml(src.read("ppt/slides/slide1.xml"))
        with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                if item.filename in {
                    "ppt/slides/slide1.xml",
                    "ppt/media/image1.png",
                    "ppt/media/image2.png",
                }:
                    continue
                dst.writestr(item, src.read(item.filename))
            dst.writestr("ppt/slides/slide1.xml", new_slide)
            dst.writestr("ppt/media/image1.png", FULL_IMG.read_bytes())
            dst.writestr("ppt/media/image2.png", ZOOM_IMG.read_bytes())


if __name__ == "__main__":
    write_pptx()
    print(OUT)
    print(FULL_IMG)
    print(ZOOM_IMG)
