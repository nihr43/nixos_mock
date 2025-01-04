import uuid
import time
import ipaddress
import json

from concurrent.futures import ThreadPoolExecutor
import subprocess


def cleanup(key):
    r = subprocess.run(
        "incus ls -f json", shell=True, capture_output=True, text=True, check=True
    )
    j = json.loads(r.stdout)
    for i in j:
        if i["name"].startswith(key) and i["description"] == "nixos-mock":
            subprocess.run(
                f"incus rm {i["name"]} --force",
                shell=True,
                text=True,
                check=True,
            )
            print(f"{i["name"]} deleted")


class Node:
    def __init__(self, key, image):
        rnd = str(uuid.uuid4())[0:4]
        self.name = f"{key}-{rnd}"
        cmd = f"incus init images:{image} {self.name} --vm -c limits.cpu=4 -c limits.memory=8GB -c security.secureboot=false"
        subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        subprocess.run(
            f"incus config device override {self.name} root size=32GB",
            shell=True,
            text=True,
            check=True,
        )
        subprocess.run(
            f"incus config set -p {self.name} description 'nixos-mock'",
            shell=True,
            text=True,
            check=True,
        )
        subprocess.run(f"incus start {self.name}", shell=True, text=True, check=True)
        self.wait_until_ready()
        self.install_ssh()
        print(f"{self.name} created")

    def install_ssh(self):
        print(f"configuring {self.name}")
        cmd = f"incus file push src/initial.nix {self.name}/etc/nixos/configuration.nix"
        subprocess.run(cmd, shell=True, text=True, check=True)
        cmd = f"incus file push src/ssh-keys.nix {self.name}/etc/nixos/ssh-keys.nix"
        subprocess.run(cmd, shell=True, text=True, check=True)
        cmd = f"incus exec {self.name} -- su -c 'nixos-rebuild switch'"
        subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

    def wait_until_ready(self):
        """
        waits until an instance is cli executable (not ssh)
        """
        print(f"waiting for lxd agent on {self.name}")
        i = 0
        while i < 30:
            i += 1
            time.sleep(1)
            try:
                subprocess.run(
                    f"incus exec {self.name} -- hostname",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except subprocess.CalledProcessError:
                continue
            return

        raise TimeoutError("timed out waiting")

    def get_valid_ipv4(self, interface):
        """
        ipv4 addresses can take a moment to be assigned on boot, so
        inst.state().network['eth0']['addresses'][0]['address'] is not reliable.
        This waits until a valid address is assigned and returns it.
        """
        print("waiting for valid ipv4 address on", self.name)
        i = 0
        while i < 30:
            i += 1
            time.sleep(1)
            candidate_ip = self.inst.state().network[interface]["addresses"][0][
                "address"
            ]
            try:
                ipaddress.IPv4Address(candidate_ip)
                print("found {} at {}".format(self.name, candidate_ip))
                return candidate_ip
            except ipaddress.AddressValueError:
                continue
            except ConnectionResetError:
                continue
            return

        raise TimeoutError("timed out waiting")

    def get_gateway(self):
        cmd = subprocess.run(
            "incus network ls -f json",
            shell=True,
            capture_output=True,
            text=True,
        )
        js = json.loads(cmd.stdout)
        for n in js:
            if "/1.0/profiles/default" in n["used_by"]:
                print(n["name"])
                print(n["config"]["ipv4.address"])


def main():
    key = "nixos-mock"
    count = 3

    cleanup(key)

    def create_node(_):
        return Node(key, "nixos/24.11")

    with ThreadPoolExecutor(max_workers=3) as pool:
        nodes = list(pool.map(create_node, range(count)))  # noqa


if __name__ == "__main__":
    main()
