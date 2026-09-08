"""Reuse a Lab draw list when only electrical component states changed.

Geometry, camera, mode and visual-setting changes always use the normal renderer.
Painter order is retained, including opaque blocks in front of the wiring.
"""
from domain.blocks import BlockType as B


def frame_key(app, can_cache, animated):
    if not (app.redstoneLabActive and app.interactionMode and can_cache
            and not animated and not app.lightingEnabled and not app.xrayEnabled
            and len(app.world.blocks) > 1000):
        return None
    return (app.renderer.viewRotation, app.zoomLevel, app.renderer.offsetX,
            app.renderer.offsetY, app.screen.get_size(), app.redstoneLabCutaway,
            app.redstoneLabCircuitKey, app._worldSurfaceMargin)


def reuse(app, key):
    previous = getattr(app, '_labDrawList', None)
    if key is None or previous is None or previous['key'] != key:
        return None
    if previous['blocks'] != app.world.blocks:
        return None
    states = app.world.blockProperties
    if previous['states'].keys() != states.keys():
        return None
    changed = [pos for pos, state in states.items() if vars(state) != previous['states'][pos]]
    allowed = {B.REDSTONE_DUST, B.REDSTONE_TORCH, B.REDSTONE_WALL_TORCH,
               B.REPEATER, B.COMPARATOR, B.LEVER, B.STONE_BUTTON, B.REDSTONE_LAMP}
    for pos in changed:
        if (app.world.blocks[pos] not in allowed
                or states[pos].facing != previous['states'][pos]['facing']):
            return None
    blits = list(previous['blits'])
    rotation = app.renderer.viewRotation
    for pos in changed:
        index = previous['indices'].get(pos)
        if index is None:
            continue
        block = app.world.blocks[pos]
        props = states[pos]
        if block == B.REDSTONE_LAMP:
            sprite = app.assetManager.redstoneLampSprites[props.powered]
        else:
            sprite = app.assetManager.getDetailSprite(block, props.facing.in_view(rotation),
                props.comparatorSubtract if block == B.COMPARATOR else props.isOpen,
                props.slabPosition, powered=props.powered, power=props.redstonePower,
                delay=props.repeaterDelay, locked=props.repeaterLocked,
                connections=app._rotateRedstoneConnectionMask(app._redstoneConnectionMask(*pos),rotation),
                up_connections=app._rotateRedstoneConnectionMask(app._redstoneUpConnectionMask(*pos),rotation))
        sprite = app.assetManager.getScaledSprite(sprite,app.zoomLevel,
            flipped=block == B.REDSTONE_LAMP and rotation in (1,3))
        blits[index] = (sprite,blits[index][1])
    previous['blits'] = blits
    previous['states'] = {pos: vars(state).copy() for pos,state in states.items()}
    return blits


def remember(app, key, indices, blits):
    app._labDrawList = None if key is None else dict(key=key, indices=indices,
        blits=blits, blocks=dict(app.world.blocks),
        states={pos:vars(state).copy() for pos,state in app.world.blockProperties.items()})
