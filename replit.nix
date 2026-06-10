{ pkgs, ... }: {
  deps = [
    pkgs.python310
    pkgs.python310Packages.pip
    pkgs.python310Packages.pillow
    pkgs.chromium
  ];
  env = {
    PYTHONPATH = "${pkgs.python310Packages.pillow}/${pkgs.python310.sitePackages}:$PYTHONPATH";
  };
}
