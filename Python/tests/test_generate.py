"""A generátor alapvizsgálatai: `pytest` a projekt gyökeréből."""
import copy
import ipaddress
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generate  # noqa: E402
import verify    # noqa: E402


def load():
    inv = generate.load_yaml(ROOT / "inventory" / "network.yml")
    sec = generate.load_yaml(ROOT / "inventory" / "secrets.yml")
    return inv, sec


@pytest.fixture(scope="module")
def model():
    inv, sec = load()
    return generate.Model(inv, sec)


@pytest.fixture(scope="module")
def rendered(model):
    env = generate.make_env()
    return {d["hostname"]: generate.render(env, d) for d in model.devices()}


def test_inventory_valid(model):
    assert generate.validate(model) == [] or generate.validate(model) is None


def test_all_devices_rendered(rendered):
    expected = {"ISP", "R-BP", "R-DEB", "R-GYR", "R-UGY", "ASA-BP", "Core-1", "Core-2",
                "SW-A1", "SW-A2", "SW-FW", "SW-DEB", "SW-GYR", "SW-UGY"}
    assert set(rendered) == expected


def test_no_unrendered_jinja(rendered):
    for host, text in rendered.items():
        assert "{{" not in text and "{%" not in text, host
        assert "None" not in text.split(), host


def test_every_config_has_hostname_and_end(rendered):
    for host, text in rendered.items():
        assert f"hostname {host}" in text
        assert text.rstrip().endswith("end") or text.rstrip().endswith("write memory"), host


def test_strict_undefined_catches_missing_key():
    inv, sec = load()
    inv = copy.deepcopy(inv)
    del inv["sites"]["deb"]["wan"]
    with pytest.raises(Exception):
        m = generate.Model(inv, sec)
        env = generate.make_env()
        for d in m.devices():
            generate.render(env, d)


def test_placeholder_secret_rejected():
    inv, sec = load()
    sec = copy.deepcopy(sec)
    first = next(k for k, v in sec.items() if isinstance(v, str))
    sec[first] = "CHANGE_ME"
    m = generate.Model(inv, sec)
    with pytest.raises(Exception):
        errs = generate.validate(m)
        if errs:
            raise ValueError(errs)


def test_tunnel_symmetry(rendered, model):
    """A hub és a telephely tunnelcíme/-célja kölcsönösen egyezik."""
    bp = rendered["R-BP"]
    for site, host in (("deb", "R-DEB"), ("gyr", "R-GYR"), ("ugy", "R-UGY")):
        s = model.inv["sites"][site]
        assert f"tunnel destination {s['wan']['ip']}" in bp
        assert f"ip address {s['tunnel']['hub_ip']}" in bp
        assert f"tunnel destination" in rendered[host]


def test_unique_ips_per_config(rendered):
    for host, text in rendered.items():
        ips = re.findall(r"^\s*ip address (\d+\.\d+\.\d+\.\d+) ", text, re.M)
        assert len(ips) == len(set(ips)), host


def test_no_overlapping_wan_subnets(model):
    nets = []
    for s in model.inv["sites"].values():
        w = s["wan"]
        nets.append(ipaddress.ip_network(f"{w['ip']}/{w.get('prefix', 30)}", strict=False))
    for i, a in enumerate(nets):
        for b in nets[i + 1:]:
            assert not a.overlaps(b)


@pytest.mark.parametrize("dev", ["ISP", "R-BP", "R-DEB", "R-GYR", "R-UGY", "ASA-BP", "Core-1", "Core-2",
                                 "SW-FW", "SW-A1", "SW-A2", "SW-DEB", "SW-GYR", "SW-UGY"])
def test_verify_matches_live_fixture(dev):
    fx = ROOT / "tests" / "fixtures"
    assert verify.main([dev, str(fx / f"{dev}.txt"), "--strict"]) == 0
