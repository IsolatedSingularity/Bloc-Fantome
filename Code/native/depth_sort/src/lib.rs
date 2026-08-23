use std::slice;

fn depth(rotation: i32, x: i32, y: i32, z: i32) -> i32 {
    match rotation {
        0 => x + y + z,
        1 => -y + x + z,
        2 => -x - y + z,
        _ => y - x + z,
    }
}

/// Sort packed xyz coordinates by Bloc Fantome's painter key.
///
/// Returns 0 on success, 1 for invalid pointers, and 2 for invalid rotation.
#[no_mangle]
pub unsafe extern "C" fn bf_sort_positions(
    coordinates: *const i32,
    count: usize,
    rotation: i32,
    output_indices: *mut u32,
    output_depths: *mut i32,
) -> i32 {
    if rotation < 0 || rotation > 3 {
        return 2;
    }
    if count == 0 {
        return 0;
    }
    if coordinates.is_null() || output_indices.is_null() || output_depths.is_null() {
        return 1;
    }

    let coordinates = slice::from_raw_parts(coordinates, count * 3);
    let output_indices = slice::from_raw_parts_mut(output_indices, count);
    let output_depths = slice::from_raw_parts_mut(output_depths, count);
    let mut indices: Vec<usize> = (0..count).collect();
    indices.sort_unstable_by_key(|index| {
        let offset = index * 3;
        let x = coordinates[offset];
        let y = coordinates[offset + 1];
        let z = coordinates[offset + 2];
        (depth(rotation, x, y, z), z, x, y)
    });

    for (destination, index) in indices.into_iter().enumerate() {
        let offset = index * 3;
        let x = coordinates[offset];
        let y = coordinates[offset + 1];
        let z = coordinates[offset + 2];
        output_indices[destination] = index as u32;
        output_depths[destination] = depth(rotation, x, y, z);
    }
    0
}
