from pathlib import Path
p=Path('tests/test_app_integration.py');s=p.read_text()
s=s.replace('self.assertEqual(len(tutorial.TUTORIAL_STEPS), 20)','self.assertEqual(len(tutorial.TUTORIAL_STEPS), 27)')
a=s.index('    def test_advanced_tutorial_uses_dedicated');b=s.index('    def test_guided_exit_restores_tools',a)
s=s[:a]+'''    def test_linear_tour_starts_immediately_and_restores_original(self):
        original=dict(self.app.world.blocks)
        self.app._beginTutorial(advanced=True)
        try:
            self.assertFalse(self.app.tutorialScreen.menuOpen)
            self.assertEqual(self.app.tutorialScreen.lesson['id'],'welcome')
            self.assertNotEqual(dict(self.app.world.blocks),original)
        finally:self.app.tutorialScreen.hide()
        self.assertEqual(dict(self.app.world.blocks),original)

    def test_linear_tour_next_back_and_direct_jump_always_replace_example(self):
        self.app._beginTutorial(advanced=False)
        tour=self.app.tutorialScreen
        try:
            original_example=dict(self.app.world.blocks)
            self.app._placeBlockWithUndo(1,1,2,app_module.BlockType.GOLD_BLOCK)
            tour._onNextClick()
            self.assertEqual(tour.currentStep,1)
            self.assertEqual(self.app.world.getBlock(1,1,2),app_module.BlockType.AIR)
            tour._onBackClick()
            self.assertEqual(dict(self.app.world.blocks),original_example)
            for index,page in enumerate(tour.TUTORIAL_STEPS):
                tour.selectLesson(index)
                self.assertEqual(tour.lesson['id'],page['id'])
                self.assertTrue(self.app.world.blocks)
                self.assertEqual(self.app.hotbar,[app_module.BlockType[n.upper()] for n in page['icons']])
                self.assertFalse(page['goals'])
                self.assertGreater(self.app.zoomLevel,0)
            tour._onNextClick()
            self.assertFalse(tour.visible)
        finally:
            if tour.visible:tour.hide()

    def test_tour_reset_restores_page_after_optional_edits(self):
        self.app._beginTutorial(advanced=True);tour=self.app.tutorialScreen
        try:
            tour.selectLesson(3);before=dict(self.app.world.blocks)
            self.app._placeBlockWithUndo(1,1,2,app_module.BlockType.DIAMOND_BLOCK)
            tour.selectLesson(3,retry=True)
            self.assertEqual(dict(self.app.world.blocks),before)
        finally:tour.hide()

    def test_tour_circuit_can_be_tested_without_gating_next(self):
        self.app._beginTutorial(advanced=True);tour=self.app.tutorialScreen
        try:
            index=next(i for i,p in enumerate(tour.TUTORIAL_STEPS) if p['id']=='redstone')
            tour.selectLesson(index)
            self.assertTrue(self.app._interactBlock(10,14,3))
            self.app.redstone.update(100)
            self.assertTrue(self.app.world.getBlockProperties(15,14,3).powered)
            tour._onNextClick();self.assertEqual(tour.currentStep,index+1)
        finally:tour.hide()

    def test_tour_horror_reveal_is_local_and_once_per_page(self):
        self.app._beginTutorial(advanced=True);tour=self.app.tutorialScreen
        try:
            tour.selectLesson(next(i for i,p in enumerate(tour.TUTORIAL_STEPS) if p['is_horror']))
            with patch.object(self.app,'_revealGuidedAnomaly') as reveal:
                self.app.renderer.viewRotation=(self.app.renderer.viewRotation+1)%4
                tour.observe(self.app)
                self.app.renderer.viewRotation=(self.app.renderer.viewRotation+1)%4
                tour.observe(self.app)
                reveal.assert_called_once()
        finally:tour.hide()

''' +s[b:]
s=s.replace('        self.app._renderPanel()\n        before=dict(self.app.world.blocks)','        self.app._renderPanel()\n        panel.render_browser(self.app)\n        self.assertEqual(panel.cards[0][0].y,panel.cards[1][0].y)\n        self.assertLess(panel.cards[0][0].right,panel.cards[1][0].left)\n        before=dict(self.app.world.blocks)')
s=s.replace("        self.app._renderPanel()\n        self.assertEqual(panel.click(panel.confirm.center)","        self.app._renderPanel()\n        panel.render_browser(self.app)\n        self.assertEqual(panel.click(panel.confirm.center)")
p.write_text(s)
p=Path('tests/test_public_contract.py');s=p.read_text();a=s.index('    from engine.tutorial_lessons import GETTING_STARTED, HANDBOOK');b=s.index('    assert _digest(blocFantome.DIMENSION_WEATHER)',a)
s=s[:a]+'''    from engine.tutorial_lessons import TOUR
    assert len(tutorial) == len(TOUR) == 27
    assert len({step['id'] for step in TOUR}) == len(TOUR)
    assert all(not step['goals'] and step['hint'] for step in TOUR)
    assert sum(bool(step['is_horror']) for step in TOUR) == 1
'''+s[b:];p.write_text(s)
p=Path('tests/test_biomes.py');s=p.read_text().replace('0<=z<64','0<=z<256');p.write_text(s)
