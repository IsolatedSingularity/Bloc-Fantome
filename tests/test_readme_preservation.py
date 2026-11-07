"""Keep the illustrated README's literary sequence and closing gallery intact."""
import hashlib
from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.core
ROOT = Path(__file__).resolve().parents[1]


def test_canonical_passages_remain_in_order():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    anchors = (
        '<!-- The gallery remembers those who visited. -->',
        '## Overview',
        '*The world remembers every block you place.*',
        '> *Some doors, once opened, cannot be closed.*',
        '## Features',
        '### Worlds Beyond the Frame',
        '### Terrain Slices',
        '<sub>Have we met before?</sub>',
        '<sub>Wouldn\'t I?</sub>',
        '## Interactive Tutorial',
        '### Overworld',
        '### Nether',
        '### The End',
        '*The sky knows when you are watching.*',
        "<sub>L'eau sait où elle veut aller.</sub>",
        '<sub>Elle trouve toujours un chemin vers le bas.</sub>',
        "<sub>Tu peux essayer de l'arrêter.</sub>",
        '<sub>Construire des murs. Placer des blocs.</sub>',
        '<sub>Elle attendra.</sub>',
        '<sub>Elle a toujours attendu.</sub>',
        '## The Geometry of Blocks',
        '### Isometric Projection',
        '### Depth Ordering',
        '### Sparse World Representation',
        '### Liquid Dynamics',
        '### Light Propagation',
        '## Controls',
        '## Quick Start',
        '## Acknowledgments',
    )
    cursor = 0
    for anchor in anchors:
        found = text.find(anchor, cursor)
        assert found >= 0, f'Missing or reordered canonical passage: {anchor}'
        cursor = found + len(anchor)


def test_acknowledgments_and_gallery_are_unchanged():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    ending = text[text.index('## Acknowledgments'):]
    # Owner-restored end matter at 48d03eaa, with universal newline normalization.
    assert hashlib.sha256(ending.encode('utf-8')).hexdigest() == (
        'f3f69304c8d188eca543a8925e8a1beb71e2249194d1f5019c6d494dd9e8557d'
    ), 'Preserve the acknowledgments, author credit and complete closing gallery.'


def test_addendum_is_modular_and_uses_local_still_images():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert '<!-- Artistic document:' in text[:500]
    section = text.split('## A little farther\n', 1)[1].split('## Acknowledgments', 1)[0]
    assert not re.search(r'^## ', section, re.MULTILINE)
    images = re.findall(r'!\[[^\]]+\]\((docs/media/3\.3/[^)]+)\)', section)
    assert {Path(path).name for path in images} == {
        'bastion.png', 'fortress.png', 'taiga.png', 'end-islands.png',
    }
    for path in images:
        assert (ROOT / path).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), path
    assert '<p align="center"><sub>La brume passe. L\'horizon reste.</sub></p>' in section
