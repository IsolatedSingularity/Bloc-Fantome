"""Source-rig integrity, finite encounter lifecycle and physical consumption."""
import os,sys
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
import numpy as np
import pygame
import pytest
from ui.opening_scene import OpeningScene
from ui.opening_rig import ThornRig
from ui.opening_environment import AbyssGround

@pytest.fixture(scope='module')
def scene():
    pygame.init();pygame.mixer.set_num_channels(32)
    value=OpeningScene((1200,800),None,effects_volume=0)
    value.update(5);value.place();value.update(5);value.activate('door');value.update(value.RISE_DURATION)
    yield value
    value.close()

def test_source_rig_has_real_skin_weights_and_nontrivial_motion(scene):
    rig=scene.encounter.rig
    assert len(rig.parents)==161
    assert len(rig.data['positions'])//3==2710
    np.testing.assert_allclose(rig.data['weights'].sum(1),1,atol=1e-6)
    previous=None;changes=[]
    for t in np.arange(5,40,.25):
        mesh,head=rig.geometry(float(t))
        assert np.isfinite(mesh).all() and np.isfinite(head).all()
        if previous is not None:changes.append(np.linalg.norm(mesh[:,:3]-previous,axis=1).mean())
        previous=mesh[:,:3].copy()
    assert np.percentile(changes,25)>.04

def test_source_pose_rotation_preserves_rigid_bones(scene):
    rig=scene.encounter.rig
    for t in (5,9,12,18,24,29,35,39):
        pose,_=rig.pose(t)
        rotation=pose[:,:3,:3]
        np.testing.assert_allclose(rotation@rotation.swapaxes(-1,-2),np.tile(np.eye(3),(161,1,1)),atol=1e-4)


def test_import_keeps_late_source_motion_instead_of_freezing(scene):
    rig=scene.encounter.rig
    motion=rig.data['rotation_51A']
    # The second half contains the overturn. An absolute-frame/delta mixup
    # exhausted this animation near its beginning and froze every late frame.
    assert np.linalg.norm(motion[140]-motion[200])>1
    assert np.linalg.norm(motion[200]-motion[240])>1


def test_planted_palms_and_feet_hold_the_arcade(scene):
    rig=scene.encounter.rig
    for t in np.arange(10,15,.2):
        pose,origin=rig.pose(float(t))
        for _,_,end,target,_,strength in rig.contacts(t):
            assert strength==pytest.approx(1)
            actual=pose[end,3,:3][[0,2,1]]*(1,-1,1)*rig.SCALE+origin
            np.testing.assert_allclose(actual,target,atol=.002)


def test_three_skull_contacts_hit_the_stone_before_recoil(scene):
    rig=scene.encounter.rig
    for hit in (25.45,26.55,27.65):
        before=rig.geometry(hit-.1)[1]
        contact=rig.geometry(hit)[1]
        after=rig.geometry(hit+.6)[1]
        np.testing.assert_allclose(contact,(13.2,21.6,49),atol=.002)
        assert np.linalg.norm(before-contact)>20
        assert np.linalg.norm(after-contact)>20


def test_distant_monument_is_pulled_in_before_disappearing(scene):
    mesh=scene.meshes['distant']
    early,_=scene.encounter.surroundings(mesh,(0,0,0),34,33,6)
    late,_=scene.encounter.surroundings(mesh,(0,0,0),38,33,6)
    assert len(early[0])==len(late[0])==len(mesh[0])
    assert np.linalg.norm(early[0][:,:,:3]-late[0][:,:,:3])>100
    final,_=scene.encounter.surroundings(mesh,(0,0,0),39,33,6)
    assert not len(final[0])

def test_prior_monument_never_retracts_during_camera_travel(scene):
    original_phase=scene.phase
    scene.phase='approach'
    for age in (0,4,8,12,15):
        scene.elapsed=scene.phase_at+age
        meshes=scene._visible_meshes()
        for name in ('fixed','vein','foundations'):
            assert any(mesh is scene.meshes[name] and tuple(offset)==(0,0,0) for mesh,offset in meshes)
    scene.phase=original_phase

def test_consumption_moves_masonry_before_removing_it(scene):
    encounter=scene.encounter
    assert encounter.masonry(29) is None
    first=encounter.masonry(30)[0][0]
    later=encounter.masonry(35)[0][0]
    assert len(later[0])<=len(first[0]) and len(later[0])>0
    assert np.isfinite(later[0]).all()
    final=encounter.masonry(44)[0][0]
    assert not len(final[0]) and not len(final[1])

def test_ground_is_connected_and_continuously_animated():
    ground=AbyssGround()
    first=ground.mesh(0);next_frame=ground.mesh(1/60)
    assert first.shape==next_frame.shape
    assert np.max(abs(first[:,:,:3]-next_frame[:,:,:3]))<.02
    assert not np.array_equal(first[:,:,:3],next_frame[:,:,:3])

def test_encounter_finishes_without_input_and_ignores_skip(scene):
    scene.phase='sanctuary';scene.activate('heart')
    before=scene.elapsed
    for event in (pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE),
                  pygame.event.Event(pygame.KEYDOWN,key=pygame.K_q),
                  pygame.event.Event(pygame.MOUSEWHEEL,y=8),
                  pygame.event.Event(pygame.WINDOWFOCUSLOST)):
        scene.handle_event(event)
    scene.update(20)
    assert scene.elapsed==before+20 and not scene.closed
    assert scene.target_zoom==1 and not scene.orbit_keys and not scene.targets()
    scene.update(24)
    assert scene.closed


def test_muted_score_still_runs_and_releases_channel():
    from ui.opening_audio import OpeningAudio
    pygame.mixer.init();pygame.mixer.set_num_channels(32)
    audio=OpeningAudio(0)
    audio.start_encounter();audio.update_encounter(20,1/60)
    assert pygame.mixer.Channel(27).get_volume()==0
    assert pygame.mixer.Channel(27).get_busy()
    audio.close()
    assert not pygame.mixer.Channel(27).get_busy()
