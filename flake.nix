{
  description = "terminal astrology UI wrapping the astrolog cli";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;
        astro-tui = python.pkgs.buildPythonApplication {
          pname = "astro-tui";
          version = "0.1.0";
          format = "setuptools";
          src = self;
          propagatedBuildInputs = [ python.pkgs.textual ];
          nativeCheckInputs = [ python.pkgs.pytest pkgs.astrolog ];
          checkPhase = ''
            runHook preCheck
            # parser tests that need the astrolog binary get it from PATH
            python -m pytest tests/ -q
            runHook postCheck
          '';
          meta = {
            description = "terminal astrology UI: natal charts, transits, synastry, lore";
            mainProgram = "astro-tui";
          };
        };
      in
      {
        packages.default = astro-tui;
        packages.astro-tui = astro-tui;
        devShells.default = pkgs.mkShell {
          buildInputs = [ pkgs.astrolog python python.pkgs.textual python.pkgs.pytest ];
        };
        apps.default = flake-utils.lib.mkApp { drv = astro-tui; };
      });
  nixConfig = {
    extra-substituters = [ "https://cache.nixos.org" ];
  };
}
