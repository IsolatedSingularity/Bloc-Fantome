from pathlib import Path
p=Path('Code/engine/scene_cache.py');s=p.read_text().replace('b"BFC6"','b"BFC7"').replace('struct.Struct("<hhhHHBBBBBB")','struct.Struct("<hhhHHBBBBBBBBBBii")')
s=s.replace('door_half, hinge, liquid = values','door_half, hinge, liquid, oxidation, power, delay, state_flags, capture_index, palette = values')
s=s.replace('                doorHinge=DoorHinge.RIGHT if hinge else DoorHinge.LEFT,','''                doorHinge=DoorHinge.RIGHT if hinge else DoorHinge.LEFT,
                oxidationStage=oxidation, redstonePower=power, repeaterDelay=delay,
                powered=bool(state_flags & 1), repeaterLocked=bool(state_flags & 2),
                pistonExtended=bool(state_flags & 4), sticky=bool(state_flags & 8),
                comparatorSubtract=bool(state_flags & 16),
                sourceCapture=metadata["captures"][capture_index], sourcePalette=palette,''')
s=s.replace('width <= 256 and 1 <= depth <= 256','width <= 512 and 1 <= depth <= 512')
s=s.replace('    metadata = json.dumps(', '    captures = sorted({props.sourceCapture for *_, props, liquid in staged if props is not None})\n    capture_indices = {name: index for index, name in enumerate(captures)}\n    metadata = json.dumps(')
s=s.replace('"scene": serialized_scene}', '"scene": serialized_scene, "captures": captures}')
s=s.replace('                door_half, hinge, liquid,','''                door_half, hinge, liquid,
                props.oxidationStage if props else 0,
                props.redstonePower if props else 0,
                props.repeaterDelay if props else 1,
                (int(props.powered) | int(props.repeaterLocked) << 1 |
                 int(props.pistonExtended) << 2 | int(props.sticky) << 3 |
                 int(props.comparatorSubtract) << 4) if props else 0,
                capture_indices[props.sourceCapture] if props else -1,
                props.sourcePalette if props else -1,''')
p.write_text(s)
