{ pkgs }:
{
  deps = [
    pkgs.python311Full
    pkgs.chromium
    pkgs.chromedriver
    pkgs.curl
    pkgs.zip
    pkgs.unzip
  ];
}
