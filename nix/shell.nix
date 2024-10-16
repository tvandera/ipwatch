{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShellNoCC {
  packages = with pkgs; [
    (python3.withPackages (
	ps: [
		 ps.flask 
		 ps.requests
		 ps.pandas
		 ps.pip
		 ps.wakeonlan
	]))
    curl
    jq
  ];
}
