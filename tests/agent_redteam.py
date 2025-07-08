import yaml  # type: ignore

from brain.agents.redteam_agent import suggest_guard_patches


def test_guard_patch_generation():
    current_filters = {"max_position": 100}
    patch = suggest_guard_patches(current_filters)
    yaml_str = yaml.safe_dump(patch, sort_keys=False)

    loaded = yaml.safe_load(yaml_str)
    # Expect one patch modifying /max_position to 110
    patches = loaded.get("patches")
    assert patches and isinstance(patches, list)
    entry = patches[0]
    assert entry["path"] == "/max_position"
    assert entry["operation"] == "replace"
    assert entry["value"] == 110 