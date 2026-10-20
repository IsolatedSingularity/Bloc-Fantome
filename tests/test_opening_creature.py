"""Contact/kinematic contracts for the isolated authored creature proof."""
import numpy as np
import pytest
from ui.opening_creature import CONTACTS, HIGH_HANDS, DURATION, sample, body_mesh, hinge
from ui.opening_geometry import sanctuary


def test_contacts_are_real_exposed_architectural_surfaces():
    cells=sanctuary()
    for point in np.vstack((CONTACTS,HIGH_HANDS)):
        below=tuple(np.floor(point-(0,0,.01)).astype(int))
        above=tuple(np.floor(point).astype(int))
        assert below in cells,(point,below)
        assert above not in cells,(point,above)


def test_planted_hands_do_not_slide_during_weight_transfer_or_contortion():
    for t in np.linspace(6.2,11.8,141):
        pose=sample(t)
        np.testing.assert_array_equal(pose.contacts[:2],HIGH_HANDS)
        np.testing.assert_array_equal(pose.contacts[2:],CONTACTS[2:])
        assert all(pose.planted)


def test_bone_lengths_and_finite_geometry_over_entire_sequence():
    for t in np.linspace(0,DURATION,281):
        pose=sample(t)
        lengths=np.linalg.norm(np.diff(pose.limbs,axis=1),axis=2)
        np.testing.assert_allclose(lengths,((20,20),(20,20),(18,18),(18,18)),atol=1e-10)
    for t in (0,2.4,5.3,8.55,9.7,13.5):
        mesh=body_mesh(sample(t))
        assert np.isfinite(mesh).all()
        assert mesh.shape[1:]==(4,9)


def test_held_pose_is_still_and_seeking_has_no_state():
    a=sample(7.4);b=sample(7.9)
    np.testing.assert_array_equal(a.limbs,b.limbs)
    np.testing.assert_array_equal(a.spine,b.spine)
    sample(14)
    np.testing.assert_array_equal(sample(7.4).limbs,a.limbs)
    for fps in (24,30,60,144):
        t=0
        for _ in range(fps*7):t+=1/fps
        np.testing.assert_allclose(sample(t).limbs,sample(7).limbs,atol=1e-9)


def test_eye_reveal_is_brief_and_body_pull_releases_only_one_support():
    assert sample(8).eye==0
    assert sample(9.7).eye==1
    assert sample(10.3).eye==0
    pose=sample(13.5)
    assert pose.planted==(False,True,True,True)
    np.testing.assert_allclose(pose.contacts[0],HIGH_HANDS[0]+(2,9,7))
    with pytest.raises(ValueError):hinge(np.zeros(3),np.ones(3)*100,(0,0,1),20,20)


def test_sampled_creature_surfaces_clear_architecture_through_motion():
    cells=sanctuary()
    def encode(points):
        p=np.floor(points).astype(np.int64)
        return (p[...,0]+128)*65536+(p[...,1]+128)*256+p[...,2]+64
    occupied=encode(np.asarray(list(cells)))
    extracted={p for p in cells if -12<=p[0]<=-9 and 16<=p[1]<=17 and 38<=p[2]<=39}
    damaged=encode(np.asarray([p for p in cells if p not in extracted]))
    # Broad sequence samples plus every 60 Hz sample of the violent passage.
    times=np.unique(np.r_[np.linspace(0,DURATION,71),np.arange(8.35,8.95,1/60)])
    for t in times:
        pose=sample(t)
        quads=body_mesh(pose)[...,:3][...,[0,2,1]].copy()
        quads[...,1]*=-1
        points=np.vstack((quads.reshape(-1,3),quads.mean(axis=1),
                          ((quads+np.roll(quads,1,axis=1))/2).reshape(-1,3)))
        hits=np.intersect1d(encode(points),damaged if pose.pull else occupied)
        assert not len(hits),(t,len(hits))
