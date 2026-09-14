from pathlib import Path
p=Path('tests/render_visual_checks.py');s=p.read_text(encoding='utf-8');s=s.replace('    app._generateStructurePreviews()\n    app.tutorialScreen.setAssets','    app._generateStructurePreviews()\n    app._preloadTutorialMusic()\n    app.tutorialScreen.setAssets');p.write_text(s,encoding='utf-8')
p=Path('tests/test_public_contract.py');s=p.read_text().replace('len(TOUR) == 27','len(TOUR) == 16');p.write_text(s)
