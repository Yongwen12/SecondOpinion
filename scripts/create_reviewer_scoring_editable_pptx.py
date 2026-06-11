from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


OUT = Path("reports/figures/secondopinion_reviewer_scoring_editable_v0.1.pptx")
EMU = 914400
SLIDE_W = 12192000
SLIDE_H = 6858000

NAVY = "182542"
TEAL = "007B7B"
ORANGE = "D6460B"
LIGHT_ORANGE = "FDEBDC"
WHITE = "FFFFFF"
OFFWHITE = "F8FAFC"
BORDER = "D7DEE8"
MUTED = "5F6878"
TEXT = "172033"
ARROW = "B6BFCC"


def emu(inches: float) -> int:
    return int(round(inches * EMU))


class Slide:
    def __init__(self) -> None:
        self.shapes: list[str] = []
        self.next_id = 2

    def _id(self) -> int:
        value = self.next_id
        self.next_id += 1
        return value

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str = WHITE,
        line: str = BORDER,
        line_w: int = 9000,
        name: str = "Shape",
    ) -> None:
        shape_id = self._id()
        line_xml = (
            '<a:ln w="{line_w}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
            if line
            else "<a:ln><a:noFill/></a:ln>"
        ).format(line_w=line_w, line=line)
        self.shapes.append(
            f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
    {line_xml}
  </p:spPr>
</p:sp>"""
        )

    def textbox(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        text: str,
        *,
        size: int = 10,
        color: str = TEXT,
        bold: bool = False,
        italic: bool = False,
        font: str = "Georgia",
        name: str = "Text",
        align: str = "l",
    ) -> None:
        shape_id = self._id()
        lines = text.split("\n")
        runs = []
        for idx, line in enumerate(lines):
            if idx:
                runs.append("<a:br/>")
            runs.append(
                f'<a:r><a:rPr lang="en-US" sz="{size * 100}"'
                f'{" b=\"1\"" if bold else ""}{" i=\"1\"" if italic else ""}>'
                f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="{escape(font)}"/></a:rPr><a:t>{escape(line)}</a:t></a:r>'
            )
        self.shapes.append(
            f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/>
    <a:lstStyle/>
    <a:p><a:pPr algn="{align}"/>{''.join(runs)}<a:endParaRPr lang="en-US" sz="{size * 100}"/></a:p>
  </p:txBody>
</p:sp>"""
        )


def add_card(slide: Slide, y: float, h: float, label: str, title: str, body: str, stripe: str = TEAL) -> None:
    x = 0.35
    w = 4.05
    slide.rect(x, y, w, h, fill=WHITE, line=BORDER, name=f"Card - {title}")
    slide.rect(x, y, 0.06, h, fill=stripe, line="", name=f"Stripe - {title}")
    slide.textbox(x + 0.22, y + 0.11, w - 0.38, 0.18, label, size=7, color=TEAL, bold=True, name=f"Label - {title}")
    slide.textbox(x + 0.22, y + 0.30, w - 0.38, 0.22, title, size=12, color=NAVY, bold=True, name=f"Title - {title}")
    slide.textbox(x + 0.22, y + 0.55, w - 0.38, h - 0.58, body, size=8, color=TEXT, name=f"Body - {title}")


def add_arrow(slide: Slide, y: float) -> None:
    slide.textbox(2.32, y, 0.25, 0.20, "↓", size=14, color=ARROW, bold=True, name="Flow Arrow", align="c")


def add_axis(slide: Slide, x: float, y: float, title: str, body: str, *, orange: bool = False) -> None:
    fill = LIGHT_ORANGE if orange else OFFWHITE
    line = "F0C7A9" if orange else BORDER
    color = ORANGE if orange else NAVY
    dot = ORANGE if orange else TEAL
    slide.rect(x, y, 1.92, 0.50, fill=fill, line=line, name=f"Axis - {title}")
    slide.rect(x + 0.12, y + 0.15, 0.055, 0.055, fill=dot, line=dot, name=f"Dot - {title}")
    slide.textbox(x + 0.24, y + 0.10, 1.62, 0.16, title, size=8, color=color, bold=True, name=f"Axis title - {title}")
    slide.textbox(x + 0.24, y + 0.27, 1.62, 0.22, body, size=7, color="475569", name=f"Axis body - {title}")


def build_slide_xml(slide: Slide) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_W}" cy="{SLIDE_H}"/><a:chOff x="0" y="0"/><a:chExt cx="{SLIDE_W}" cy="{SLIDE_H}"/></a:xfrm></p:grpSpPr>
      {''.join(slide.shapes)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def build_deck() -> None:
    slide = Slide()
    slide.textbox(0.35, 0.27, 3.8, 0.28, "Reviewer Opinion Scoring", size=19, color=NAVY, bold=True, name="Main title")
    slide.textbox(0.35, 0.57, 3.95, 0.22, "Neutral third-party assessment of review comments", size=8, color=MUTED, name="Subtitle")
    slide.rect(3.32, 0.30, 0.78, 0.17, fill="F3F6FB", line=BORDER, name="Pill")
    slide.textbox(3.43, 0.34, 0.57, 0.11, "VP1", size=7, color=NAVY, bold=True, name="Pill text", align="c")

    add_card(
        slide,
        0.86,
        0.68,
        "1. REVIEW DATA",
        "Official Review Package",
        "Review text, strengths, weaknesses,\nquestions, rating and confidence.",
        stripe=NAVY,
    )
    add_arrow(slide, 1.60)
    add_card(
        slide,
        1.76,
        0.68,
        "2. NORMALIZE",
        "Structured Review Record",
        "Separate factual comments, questions,\nrequests and score justifications.",
        stripe=NAVY,
    )
    add_arrow(slide, 2.50)
    add_card(
        slide,
        2.66,
        0.78,
        "3. ATOMIC CLAIMS",
        "Extract Reviewer's Opinions",
        "Turn each review into auditable claims:\ncriticism, question, requested experiment,\nclarification request or score rationale.",
    )
    add_arrow(slide, 3.50)
    add_card(
        slide,
        3.66,
        0.62,
        "4. EVIDENCE GROUNDING",
        "Attach Paper + Prior-Art Context",
        "Ground each claim in review text, paper content,\nand external related work / dataset evidence.",
    )
    add_arrow(slide, 4.34)

    x = 0.35
    y = 4.50
    w = 4.05
    h = 1.72
    slide.rect(x, y, w, h, fill=WHITE, line=BORDER, name="Scoring dimensions card")
    slide.rect(x, y, 0.06, h, fill=TEAL, line="", name="Scoring dimensions stripe")
    slide.textbox(x + 0.22, y + 0.10, w - 0.38, 0.18, "5. SCORING DIMENSIONS", size=7, color=TEAL, bold=True, name="Scoring label")
    slide.textbox(x + 0.22, y + 0.29, w - 0.38, 0.20, "Score the Opinion, Not the Person", size=12, color=NAVY, bold=True, name="Scoring title")
    add_axis(slide, 0.56, 4.86, "Specificity", "Concrete,\nlocalized, inspectable?")
    add_axis(slide, 2.45, 4.86, "Substantiation", "Reasons, evidence,\nor comparison?")
    add_axis(slide, 0.56, 5.42, "Actionability", "Clear next step\nfor authors?")
    add_axis(slide, 2.45, 5.42, "Materiality", "Core claim or\nmargin issue?", orange=True)
    add_axis(slide, 0.56, 5.98, "Semantic Consensus", "Same concern\nacross reviews?")
    add_axis(slide, 2.45, 5.98, "Tone & Calibration", "Confidence,\nrating, civility.", orange=True)

    add_arrow(slide, 6.27)
    add_card(
        slide,
        6.47,
        0.76,
        "6. OUTPUT",
        "Reviewer Opinion Scorecard",
        "Comment-level score plus review-level profile:\nhigh-signal, under-supported, over-harsh,\nover-lenient or needs human check.",
        stripe=ORANGE,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    files = {
        "[Content_Types].xml": content_types(),
        "_rels/.rels": package_rels(),
        "docProps/core.xml": core_props(now),
        "docProps/app.xml": app_props(),
        "ppt/presentation.xml": presentation_xml(),
        "ppt/_rels/presentation.xml.rels": presentation_rels(),
        "ppt/slides/slide1.xml": build_slide_xml(slide),
        "ppt/slides/_rels/slide1.xml.rels": empty_rels(),
        "ppt/slideMasters/slideMaster1.xml": slide_master_xml(),
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": slide_master_rels(),
        "ppt/slideLayouts/slideLayout1.xml": slide_layout_xml(),
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": slide_layout_rels(),
        "ppt/theme/theme1.xml": theme_xml(),
    }
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    print(f"Wrote {OUT}")


def content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
</Types>"""


def package_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def core_props(now: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>SecondOpinion Reviewer Opinion Scoring</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>"""


def app_props() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>PowerPoint</Application>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Slides>1</Slides>
  <Company></Company>
</Properties>"""


def presentation_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle/>
</p:presentation>"""


def presentation_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>"""


def empty_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""


def slide_master_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>
  <p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>"""


def slide_master_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>"""


def slide_layout_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""


def slide_layout_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>"""


def theme_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="SecondOpinion">
  <a:themeElements>
    <a:clrScheme name="SecondOpinion">
      <a:dk1><a:srgbClr val="182542"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="172033"/></a:dk2><a:lt2><a:srgbClr val="F8FAFC"/></a:lt2>
      <a:accent1><a:srgbClr val="007B7B"/></a:accent1><a:accent2><a:srgbClr val="D6460B"/></a:accent2>
      <a:accent3><a:srgbClr val="5F6878"/></a:accent3><a:accent4><a:srgbClr val="D7DEE8"/></a:accent4>
      <a:accent5><a:srgbClr val="FDEBDC"/></a:accent5><a:accent6><a:srgbClr val="F8FAFC"/></a:accent6>
      <a:hlink><a:srgbClr val="007B7B"/></a:hlink><a:folHlink><a:srgbClr val="D6460B"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="SecondOpinion">
      <a:majorFont><a:latin typeface="Georgia"/></a:majorFont>
      <a:minorFont><a:latin typeface="Georgia"/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="SecondOpinion"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme>
  </a:themeElements>
</a:theme>"""


if __name__ == "__main__":
    build_deck()
