{ pkgs ? import <nixpkgs> {} }:
let
  packages = ps:
    let
      ipwatch = ps.callPackage ./ipwatch.nix { };
    in
      [
        ipwatch
      ];
in
  pkgs.python3.withPackages packages
