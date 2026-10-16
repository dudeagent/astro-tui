{
  description = "terminal astrology UI wrapping the astrolog cli";

  inputs = {
    # pinned to a rev with a warm cache (was: nixos-unstable, where anyio
    # 4.14.2's own flaky tls tests fail in the sandbox and break the build
    # for everyone).
    nixpkgs.url = "github:NixOS/nixpkgs/fdc7b8f7b30f";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
        python = pkgs.python312;
        astro-tui = python.pkgs.buildPythonApplication {
          pname = "astro-tui";
          version = "0.1.0";
          format = "pyproject";
          src = self;
          propagatedBuildInputs = [ python.pkgs.textual ];
          nativeBuildInputs = [ python.pkgs.setuptools ];
          nativeCheckInputs = [ python.pkgs.pytest pkgs.astrolog ];
          # runtime: the app shells out to the astrolog binary, so it has to
          # be on PATH inside the app env, not just at build time.
          postFixup = ''
            wrapProgram $out/bin/astro-tui \
              --prefix PATH : ${pkgs.astrolog}/bin
          '';
          checkPhase = ''
            runHook preCheck
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
}
