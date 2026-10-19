from pathlib import Path
p=Path('tests/test_maintenance.py');s=p.read_text().replace('from domain.blocks import BlockProperties','from domain.blocks import BlockProperties\nfrom domain.world_catalog import WorldCatalog');s=s.replace('app.world=World(64,64,32,min_y=-8)','''bt=module.BlockType
    catalog=WorldCatalog(bt,bt.AIR,bt.WATER,bt.LAVA,bt.OBSIDIAN,bt.COBBLESTONE,bt.STONE,module.BLOCK_DEFINITIONS)
    app.world=World(64,64,32,min_y=-8,catalog=catalog)''');p.write_text(s)
p=Path('tests/test_public_contract.py');s=p.read_text(encoding='utf-8').replace('00a10913750fe3892de37cb42c99389b31e01a189c5f28be8431239f158f3dc2','f1d0dcb0aabb540ae8689118bb7fe235159dcc92869a482a91c4106067e5b2cb');p.write_text(s,encoding='utf-8')
p=Path('Code/engine/world.py');s=p.read_text();a=s.index('        definition = self.catalog.definitions.get(blockType)',s.index('    def _surfaceViewsForPosition'));b=s.index('        if not neighborIsOpaque((x, y, z + 1)):',a)
s=s[:a]+'''        if blockType not in self._opaqueCubeTypes:
            return range(4)
        x, y, z = pos

        def neighborIsOpaque(neighbor) -> bool:
            neighborType = self.blocks.get(neighbor, BlockType.AIR)
            return (neighborType in self._opaqueCubeTypes
                    and neighborType not in self._surfaceTransparentTypes)

'''+s[b:]
s=s.replace('        self.catalog = catalog','''        self.catalog = catalog
        # Catalog definitions are immutable; classify once rather than per face.
        self._opaqueCubeTypes = frozenset(
            block for block, definition in catalog.definitions.items()
            if definition and not any(getattr(definition, field, False) for field in
                ("transparent", "isLiquid", "isThin", "isSlab", "isStair", "isPortal", "modelKind"))
        )''');p.write_text(s)
p=Path('Code/blocFantome.py');s=p.read_text(encoding='utf-8');s=s.replace('''            and self._worldZoomFallback is not None
            and len(blocksToDraw) > 4000''','''            and len(blocksToDraw) > 4000''');s=s.replace('''            self.screen.blit(
                self._worldZoomFallback,
                (-self._worldSurfaceMargin, -self._worldSurfaceMargin),
            )''','''            if self._worldZoomFallback is not None:
                self.screen.blit(self._worldZoomFallback,
                                 (-self._worldSurfaceMargin, -self._worldSurfaceMargin))
            else:
                self.screen.blit(targetSurface,
                                 (-self._worldSurfaceMargin, -self._worldSurfaceMargin))''');p.write_text(s,encoding='utf-8')
p=Path('tests/test_natural_scenes.py');s=p.read_text();s=s.replace('            assert not splash.title_font.get_bold()','            assert splash.artwork_rect.bottom < splash._title_rect().top\n            assert abs(splash.artwork_rect.centerx-size[0]//2)<=1\n            assert not splash.title_font.get_bold()');p.write_text(s)
