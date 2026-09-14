use std::slice;

/// Sample the six-face OptiFine atlas directly into native-resolution RGB.
/// Buffers are owned by the caller and lengths are checked before access.
#[no_mangle]
pub unsafe extern "C" fn bf_cubemap_rgb(
    atlas: *const u8, atlas_len: usize, aw: usize, ah: usize,
    output: *mut u8, output_len: usize, width: usize, height: usize,
    yaw: f32, pitch: f32, vertical_center: f32,
) -> i32 {
    if atlas.is_null() || output.is_null() || aw < 3 || ah < 2 || width == 0 || height == 0
        || aw > 16384 || ah > 16384 || width > 16384 || height > 16384
        || atlas_len < aw * ah * 3 || output_len < width * height * 3
        || !yaw.is_finite() || !pitch.is_finite() || !vertical_center.is_finite() {
        return 1;
    }
    let source = slice::from_raw_parts(atlas, atlas_len);
    let dest = slice::from_raw_parts_mut(output, output_len);
    let fw = aw / 3;
    let fh = ah / 2;
    let focal = (width as f32 / 2.0) / 47.0_f32.to_radians().tan();
    let (sy, cy) = yaw.to_radians().sin_cos();
    let (sp, cp) = pitch.to_radians().sin_cos();
    let workers = if width * height >= 1_000_000 { 4 } else { 2 };
    let stripe_height = (height + workers - 1) / workers;
    std::thread::scope(|scope| {
      for (stripe, chunk) in dest[..width * height * 3].chunks_mut(stripe_height * width * 3).enumerate() {
        scope.spawn(move || {
          for (local_y, row_output) in chunk.chunks_mut(width * 3).enumerate() {
        let y = stripe * stripe_height + local_y;
        let screen_y = (height as f32 * vertical_center - y as f32 - 0.5) / focal;
        let dy = screen_y * cp + sp;
        let camera_z = cp - screen_y * sp;
        for x in 0..width {
            let screen_x = (x as f32 + 0.5 - width as f32 / 2.0) / focal;
            let dx = screen_x * cy + camera_z * sy;
            let dz = camera_z * cy - screen_x * sy;
            let axis = dx.abs().max(dy.abs()).max(dz.abs());
            let (col, row, lx, ly) = if dy.abs() == axis {
                if dy < 0.0 { (0, 0, -dz, dx) } else { (1, 0, -dz, -dx) }
            } else if dx.abs() == axis {
                if dx >= 0.0 { (2, 0, dz, -dy) } else { (1, 1, -dz, -dy) }
            } else if dz >= 0.0 { (0, 1, -dx, -dy) } else { (2, 1, dx, -dy) };
            let u = ((0.5 + 0.5 * lx / axis) * (fw - 1) as f32).round().clamp(0.0, (fw-1) as f32) as usize;
            let v = ((0.5 + 0.5 * ly / axis) * (fh - 1) as f32).round().clamp(0.0, (fh-1) as f32) as usize;
            let src = ((row * fh + v) * aw + col * fw + u) * 3;
            let dst = x * 3;
            row_output[dst..dst+3].copy_from_slice(&source[src..src+3]);
        }
    }
        });
      }
    });
    0
}

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
