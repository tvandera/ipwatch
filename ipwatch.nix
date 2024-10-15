{ lib
, buildPythonPackage
, fetchFromGitHub

, hatchling
, platformdirs
}:

buildPythonPackage {
  pname = "ipwatch";
  version = "1.0";
  pyproject = true;

  nativeBuildInputs = [
    hatchling
  ];

  propagatedBuildInputs = [
    platformdirs
  ];

  src = ./python;
}
