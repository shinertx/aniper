use super::ws_feed::LaunchEvent;

pub fn score(event: &LaunchEvent) -> f32 {
    // static heuristic until WASM hot-swap
    if event.holders_60 > 50 && event.lp > 0.5 {
        0.9
    } else {
        0.1
    }
} 