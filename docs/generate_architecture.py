#!/usr/bin/env python3
"""
Architecture diagram — Autonomous Document Intel Engine

Dependencies: pip install matplotlib
Run:          python docs/generate_architecture.py
Output:       docs/architecture.png
              docs/architecture.svg
"""

import os
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — no display required

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Colour theme ──────────────────────────────────────────────────────────────
THEME = {
    "input":   dict(face="#2E86AB", bg="#D6EAF8", edge="#1A5276"),
    "pipe":    dict(face="#27AE60", bg="#EAFAF1", edge="#1E8449"),
    "decide":  dict(face="#F4D03F", bg="#FEF9E7", edge="#D4AC0D"),
    "llm":     dict(face="#E67E22", bg="#FDEBD0", edge="#CA6F1E"),
    "config":  dict(face="#16A085", bg="#D1F2EB", edge="#117A65"),
    "store":   dict(face="#8E44AD", bg="#E8DAEF", edge="#6C3483"),
    "ui":      dict(face="#C0392B", bg="#FADBD8", edge="#922B21"),
}

FONT = "DejaVu Sans"


# ── Drawing helpers ───────────────────────────────────────────────────────────

def cluster(ax, x, y, w, h, title, key):
    """Dashed-border cluster background with a header label."""
    t = THEME[key]
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.25",
        fc=t["bg"], ec=t["edge"], lw=2.2, ls="--", zorder=1,
    ))
    ax.text(
        x + w / 2, y + h + 0.08, f"  {title}  ",
        ha="center", va="bottom", fontsize=9.5, fontweight="bold",
        color=t["edge"], fontfamily=FONT, zorder=2,
        bbox=dict(boxstyle="round,pad=0.18", fc=t["bg"], ec=t["edge"], lw=1.2),
    )


def node(ax, cx, cy, w, h, text, key, fs=8.2):
    """Filled rounded rectangle node."""
    t = THEME[key]
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.12",
        fc=t["face"], ec=t["edge"], lw=1.8, zorder=3,
    ))
    color = "#2C2C2C" if key == "decide" else "white"
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            color=color, fontfamily=FONT, zorder=4,
            linespacing=1.45, multialignment="center")


def diamond(ax, cx, cy, w, h, text, key, fs=8.2):
    """Diamond decision shape."""
    t = THEME[key]
    xs = [cx, cx + w / 2, cx, cx - w / 2]
    ys = [cy + h / 2, cy, cy - h / 2, cy]
    ax.add_patch(Polygon(
        list(zip(xs, ys)), closed=True,
        fc=t["face"], ec=t["edge"], lw=1.8, zorder=3,
    ))
    color = "#2C2C2C" if key == "decide" else "white"
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            color=color, fontfamily=FONT, zorder=4,
            linespacing=1.45, multialignment="center")


def arrow(ax, x1, y1, x2, y2, color="#555555",
          dashed=False, label="", lx=0.15, ly=0.0, rad=0.0):
    """Annotate arrow between two points."""
    ls = (0, (5, 4)) if dashed else "-"
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="->", color=color, lw=1.7,
            linestyle=ls,
            connectionstyle=f"arc3,rad={rad}",
        ),
        zorder=5,
    )
    if label:
        mx = (x1 + x2) / 2 + lx
        my = (y1 + y2) / 2 + ly
        ax.text(mx, my, label, fontsize=7.2, color=color,
                ha="left", va="center", style="italic",
                fontfamily=FONT, zorder=6)


# ── Main diagram ──────────────────────────────────────────────────────────────

def main():
    fig, ax = plt.subplots(figsize=(22, 29))
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 29)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # ── Page title ────────────────────────────────────────────────────────────
    ax.text(11, 28.4, "Autonomous Document Intel Engine",
            ha="center", va="center", fontsize=17, fontweight="bold",
            color="#2C3E50", fontfamily=FONT)
    ax.text(11, 27.85, "System Architecture  |  Python-first · LLM-fallback",
            ha="center", va="center", fontsize=10.5, color="#7F8C8D",
            fontfamily=FONT)

    # ══════════════════════════════════════════════════════════════════════════
    # CLUSTER BACKGROUNDS  (draw first so nodes sit on top)
    # ══════════════════════════════════════════════════════════════════════════
    cluster(ax, 3.8, 25.7, 14.4, 1.85, "INPUT LAYER", "input")
    cluster(ax, 0.3, 13.5,  4.2, 10.8, "CONFIGURATION", "config")
    cluster(ax, 4.8,  8.8, 12.4, 16.6, "LANGGRAPH ORCHESTRATION PIPELINE", "pipe")
    cluster(ax, 16.8, 17.6,  4.8,  7.2, "AI SERVICES  (fallback only)", "llm")
    cluster(ax, 0.5,  4.0, 21.0,  3.8, "STORAGE LAYER", "store")
    cluster(ax, 4.5,  0.5, 13.0,  3.2, "UI LAYER", "ui")

    # ══════════════════════════════════════════════════════════════════════════
    # NODES
    # ══════════════════════════════════════════════════════════════════════════

    # ── Input layer ───────────────────────────────────────────────────────────
    node(ax,  6.6, 26.6, 3.8, 0.85, "REST API\nPOST /process",       "input")
    node(ax, 11.0, 26.6, 3.8, 0.85, "Batch Mode\nDirectory Watch",   "input")
    node(ax, 15.4, 26.6, 3.8, 0.85, "Gradio Upload\nQE / VAPT",      "input")

    # ── Pipeline stages ───────────────────────────────────────────────────────
    node(ax, 11.0, 24.5, 6.5, 0.9,
         "STAGE 1  —  PARSE\nDocling  |  PDF  ·  DOCX  ·  PPTX  ·  Images  →  Structured Markdown",
         "pipe")

    diamond(ax, 11.0, 22.0, 6.8, 1.7,
            "STAGE 2  —  CLASSIFY\nPython Keyword Engine\nkeyword search  ·  regex  ·  rule sets",
            "decide")

    node(ax,  8.0, 19.2, 4.8, 0.95,
         "Deterministic Path\nconfidence  ≥  threshold\nmethod: deterministic",
         "pipe")

    node(ax, 14.0, 19.2, 4.8, 0.95,
         "STAGE 2b  —  LLM FALLBACK\nGranite-3.0-8b  /  Llama 3.1\nmethod: llm_fallback",
         "llm")

    node(ax, 11.0, 16.6, 6.5, 0.9,
         "STAGE 3  —  VALIDATE\nPydantic Schema Validation  |  field-level error reporting",
         "pipe")

    node(ax, 11.0, 14.1, 6.5, 0.9,
         "STAGE 4  —  AUDIT LOG\ndocument_id  ·  method  ·  confidence  ·  escalation_reason  ·  outcome",
         "pipe")

    node(ax, 11.0, 11.6, 6.5, 0.9,
         "STAGE 5  —  OUTPUT\nExtracted JSON  |  classification_method tagged",
         "pipe")

    # ── AI Services ───────────────────────────────────────────────────────────
    node(ax, 19.2, 22.5, 4.0, 0.95,
         "IBM Watsonx\nGranite-3.0-8b-Instruct", "llm")
    node(ax, 19.2, 20.2, 4.0, 0.95,
         "Ollama (local)\nLlama 3.1", "llm")

    # ── Configuration ─────────────────────────────────────────────────────────
    node(ax, 2.4, 22.0, 3.6, 1.1,
         "YAML Keyword\nDictionaries\nper category\n+ confidence thresholds",
         "config", fs=7.8)
    node(ax, 2.4, 19.0, 3.6, 0.95,
         "Pydantic\nDomain Schemas\nper category",
         "config")

    # ── Storage ───────────────────────────────────────────────────────────────
    node(ax,  3.4, 5.85, 3.8, 0.95, "Raw Documents\nFilesystem / S3",      "store")
    node(ax,  8.0, 5.85, 3.8, 0.95, "Extracted JSON\nSQLite → PostgreSQL", "store")
    node(ax, 12.6, 5.85, 3.8, 0.95, "Audit Logs\nAppend-only JSONL",       "store")
    node(ax, 17.8, 5.85, 3.8, 0.95, "QE Feedback\nFlagged Docs · JSONL",   "store")

    # ── UI ────────────────────────────────────────────────────────────────────
    node(ax,  8.0, 1.9, 5.0, 1.1,
         "Chainlit\nBusiness Dashboard\nWorkflow  ·  Reasoning Logs  ·  Inspector",
         "ui")
    node(ax, 14.0, 1.9, 5.0, 1.1,
         "Gradio\nQE Playground\nEdge Cases  ·  VAPT  ·  Keyword Inspector",
         "ui")

    # ══════════════════════════════════════════════════════════════════════════
    # ARROWS
    # ══════════════════════════════════════════════════════════════════════════

    P = "#2E86AB"   # input blue
    G = "#27AE60"   # pipeline green
    O = "#E67E22"   # llm orange
    V = "#16A085"   # config teal
    S = "#8E44AD"   # storage purple
    U = "#C0392B"   # ui red

    # ── Input → Parse ─────────────────────────────────────────────────────────
    arrow(ax,  6.6, 26.17, 9.4, 24.95,  P)
    arrow(ax, 11.0, 26.17, 11.0, 24.95, P, label="Structured\nMarkdown", lx=0.15)
    arrow(ax, 15.4, 26.17, 12.6, 24.95, P)

    # ── Parse → Store Raw  (left side, dashed) ────────────────────────────────
    arrow(ax, 8.0, 24.5, 3.4, 6.32, S, dashed=True,
          label="store\noriginal", lx=0.12, rad=0.05)

    # ── Parse → Classify ──────────────────────────────────────────────────────
    arrow(ax, 11.0, 24.05, 11.0, 22.85, G)

    # ── Config → Classify ─────────────────────────────────────────────────────
    arrow(ax, 4.2, 22.0, 7.6, 22.0, V, label="Keywords &\nThresholds", lx=0.12)

    # ── Classify → Deterministic ──────────────────────────────────────────────
    arrow(ax, 9.3, 21.15, 8.0, 19.67, G,
          label="confidence\n≥ threshold", lx=-2.5, ly=0.0)

    # ── Classify → LLM Fallback  (dashed) ────────────────────────────────────
    arrow(ax, 12.7, 21.15, 14.0, 19.67, O, dashed=True,
          label="confidence\n< threshold", lx=0.12)

    # ── LLM → AI Services  (dashed) ───────────────────────────────────────────
    arrow(ax, 16.4, 19.5, 17.2, 22.0,  O, dashed=True,
          label="inference\nrequest", lx=0.12)
    arrow(ax, 16.4, 18.9, 17.2, 19.7,  O, dashed=True)

    # ── Deterministic → Validate ──────────────────────────────────────────────
    arrow(ax, 8.0, 18.72, 8.9, 17.05, G,
          label="deterministic\nresult", lx=-2.6)

    # ── LLM → Validate ────────────────────────────────────────────────────────
    arrow(ax, 14.0, 18.72, 13.1, 17.05, G,
          label="llm_fallback\nresult", lx=0.12)

    # ── Config Schemas → Validate ─────────────────────────────────────────────
    arrow(ax, 4.2, 19.0, 7.75, 16.75, V, label="Domain\nSchema", lx=0.12)

    # ── Validate → Audit Log ──────────────────────────────────────────────────
    arrow(ax, 11.0, 16.15, 11.0, 14.55, G)

    # ── Audit Log → Output ────────────────────────────────────────────────────
    arrow(ax, 11.0, 13.65, 11.0, 12.05, G)

    # ── Output → JSON Store ───────────────────────────────────────────────────
    arrow(ax, 11.0, 11.15, 8.0, 6.32, S, label="persist\nresult", lx=0.12)

    # ── Audit → Audit Log Store  (dashed) ─────────────────────────────────────
    arrow(ax, 11.0, 13.65, 12.6, 6.32, S, dashed=True,
          label="persist\nlog entry", lx=0.12)

    # ── Output → Chainlit ─────────────────────────────────────────────────────
    arrow(ax, 10.1, 11.15, 8.0, 2.45, U, label="results +\nreasoning", lx=-2.2)

    # ── Output → Gradio ───────────────────────────────────────────────────────
    arrow(ax, 11.9, 11.15, 14.0, 2.45, U)

    # ── Gradio → QE Feedback ──────────────────────────────────────────────────
    arrow(ax, 14.0, 1.35, 17.8, 5.32, S, label="Flag for\nReview", lx=0.12)

    # ── Feedback → Keyword Dict  (curved feedback loop) ───────────────────────
    ax.annotate(
        "", xy=(2.4, 21.44), xytext=(17.8, 5.32),
        arrowprops=dict(
            arrowstyle="->", color=V, lw=1.7,
            linestyle=(0, (5, 4)),
            connectionstyle="arc3,rad=-0.38",
        ),
        zorder=5,
    )
    ax.text(0.55, 11.5,
            "Keyword gap\nanalysis →\nupdate YAML",
            fontsize=7.2, color=V, ha="left", va="center",
            style="italic", fontfamily=FONT, zorder=6)

    # ══════════════════════════════════════════════════════════════════════════
    # LEGEND
    # ══════════════════════════════════════════════════════════════════════════
    legend_items = [
        mpatches.Patch(fc=THEME["input"]["face"],  ec=THEME["input"]["edge"],  label="Input Layer"),
        mpatches.Patch(fc=THEME["pipe"]["face"],   ec=THEME["pipe"]["edge"],   label="Pipeline Stage"),
        mpatches.Patch(fc=THEME["decide"]["face"], ec=THEME["decide"]["edge"], label="Decision / Classification"),
        mpatches.Patch(fc=THEME["llm"]["face"],    ec=THEME["llm"]["edge"],    label="LLM / AI Service  (fallback)"),
        mpatches.Patch(fc=THEME["config"]["face"], ec=THEME["config"]["edge"], label="Configuration"),
        mpatches.Patch(fc=THEME["store"]["face"],  ec=THEME["store"]["edge"],  label="Storage"),
        mpatches.Patch(fc=THEME["ui"]["face"],     ec=THEME["ui"]["edge"],     label="UI Layer"),
    ]
    ax.legend(
        handles=legend_items, loc="lower right",
        fontsize=8.2, framealpha=0.96,
        edgecolor="#BBBBBB", facecolor="white",
        bbox_to_anchor=(0.999, 0.005),
        prop={"family": FONT},
    )

    # ══════════════════════════════════════════════════════════════════════════
    # SAVE
    # ══════════════════════════════════════════════════════════════════════════
    plt.tight_layout(pad=0.5)

    for fmt in ("png", "svg"):
        out = os.path.join(OUTPUT_DIR, f"architecture.{fmt}")
        fig.savefig(
            out, format=fmt,
            dpi=150 if fmt == "png" else None,
            bbox_inches="tight",
            facecolor="white",
        )
        print(f"Saved: {out}")

    plt.close(fig)


if __name__ == "__main__":
    main()
