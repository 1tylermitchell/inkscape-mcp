"""Unit tests for inkscape_layers tool and insert_image_layer operation."""

import base64
from pathlib import Path
import pytest

from inkscape_mcp.tools.layer_operations import inkscape_layers


@pytest.fixture
def sample_svg(tmp_path: Path) -> Path:
    svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="800" height="600" viewBox="0 0 800 600">
  <defs>
    <linearGradient id="sample_grad"/>
  </defs>
  <g inkscape:groupmode="layer" id="layer1" inkscape:label="Vector Artwork">
    <rect id="rect1" x="10" y="10" width="100" height="100" fill="red"/>
  </g>
</svg>"""
    p = tmp_path / "test_doc.svg"
    p.write_text(svg_content, encoding="utf-8")
    return p


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    # 1x1 transparent png
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    p = tmp_path / "sample_texture.png"
    p.write_bytes(png_bytes)
    return p


@pytest.mark.asyncio
async def test_layer_list_and_create(sample_svg: Path):
    res = await inkscape_layers("list", input_path=str(sample_svg))
    assert res["success"] is True
    assert len(res["data"]["layers"]) == 1
    assert res["data"]["layers"][0]["id"] == "layer1"

    # Create new layer
    res2 = await inkscape_layers("create", input_path=str(sample_svg), label="Annotations")
    assert res2["success"] is True
    assert res2["data"]["label"] == "Annotations"

    # Verify list now has 2
    res3 = await inkscape_layers("list", input_path=str(sample_svg))
    assert res3["data"]["count"] == 2


@pytest.mark.asyncio
async def test_insert_image_layer_base64_bottom(sample_svg: Path, sample_image: Path):
    output_svg = sample_svg.parent / "doc_with_bg.svg"
    res = await inkscape_layers(
        "insert_image_layer",
        input_path=str(sample_svg),
        output_path=str(output_svg),
        image_path=str(sample_image),
        label="Background Map",
        embed_mode="base64",
        opacity=0.85,
        fit="cover",
        z_index="bottom",
    )
    assert res["success"] is True
    assert res["data"]["embed_mode"] == "base64"
    assert res["data"]["z_index"] == "bottom"
    assert res["data"]["opacity"] == 0.85

    # Check resulting SVG file contents
    content = output_svg.read_text(encoding="utf-8")
    assert 'inkscape:label="Background Map"' in content
    assert 'data:image/png;base64,' in content
    assert 'preserveAspectRatio="xMidYMid slice"' in content
    assert 'opacity="0.85"' in content

    # Verify image layer is positioned as bottom underlay (before layer1)
    bg_idx = content.find('inkscape:label="Background Map"')
    l1_idx = content.find('inkscape:label="Vector Artwork"')
    assert bg_idx < l1_idx


@pytest.mark.asyncio
async def test_insert_image_layer_link_top(sample_svg: Path, sample_image: Path):
    output_svg = sample_svg.parent / "doc_with_overlay.svg"
    res = await inkscape_layers(
        "insert_image_layer",
        input_path=str(sample_svg),
        output_path=str(output_svg),
        image_path=str(sample_image),
        label="Watermark Overlay",
        embed_mode="link",
        opacity=0.5,
        fit="contain",
        z_index="top",
    )
    assert res["success"] is True
    content = output_svg.read_text(encoding="utf-8")
    assert 'inkscape:label="Watermark Overlay"' in content
    assert str(sample_image) in content
    assert 'preserveAspectRatio="xMidYMid meet"' in content

    # Top layer is placed after layer1
    wm_idx = content.find('inkscape:label="Watermark Overlay"')
    l1_idx = content.find('inkscape:label="Vector Artwork"')
    assert wm_idx > l1_idx
