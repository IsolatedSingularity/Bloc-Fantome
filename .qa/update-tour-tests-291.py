from pathlib import Path
p=Path('tests/test_app_integration.py');s=p.read_text(encoding='utf-8').replace('len(tutorial.TUTORIAL_STEPS), 27','len(tutorial.TUTORIAL_STEPS), 16')
a=s.index('    def test_tour_circuit_can_be_tested_without_gating_next');b=s.index('    def test_guided_exit_restores_tools',a)
s=s[:a]+'''    def test_tour_has_no_required_tasks_or_deferred_redstone_chapters(self):
        from engine.tutorial_lessons import TOUR
        self.assertTrue(all(not p['goals'] for p in TOUR))
        self.assertFalse(any(p['id'] in ('lab','redstone','horror') for p in TOUR))
        self.assertIn('worldmap',{p['id'] for p in TOUR})

    def test_horror_is_an_explicit_optional_detour(self):
        self.app._beginTutorial(advanced=True);tour=self.app.tutorialScreen
        try:
            tour.selectLesson(len(tour.TUTORIAL_STEPS)-1)
            tour.handleEvent(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=tour.optionalRect.center))
            self.assertEqual(tour.lesson['id'],'horror')
            tour._onBackClick()
            self.assertEqual(tour.lesson['id'],'saving')
        finally:tour.hide()

'''+s[b:]
s=s.replace('        self.app._handlePanelClick(*panel.header.center)\n        library=self.app.library\n        self.assertTrue(library.visible)', "        self.app._handlePanelClick(*self.app.lessonControlRects['biomes'].center)\n        self.assertEqual(self.app.previewBrowser.expanded,'Biomes')\n        library=self.app.library\n        library.open(self.app,'Biomes')")
p.write_text(s,encoding='utf-8')
