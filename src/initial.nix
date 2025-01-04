{ modulesPath, ... }: {
  imports = [
    "${modulesPath}/virtualisation/incus-virtual-machine.nix"
    ./ssh-keys.nix
    ./incus.nix
  ];

  system.stateVersion = "24.11";

  services.openssh = {
    enable = true;
    startWhenNeeded = false;
    settings.KbdInteractiveAuthentication = false;
    settings.PasswordAuthentication = false;
    settings.PermitRootLogin = "yes";
  };
}
