{
  description = "Anemone Python Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python3
            uv
            nodejs
          ];

          venvDir = "./.venv";
          
          nativeBuildInputs = [
            pkgs.python3Packages.venvShellHook
          ];

          postVenvCreation = ''
            unset SOURCE_DATE_EPOCH
            export UV_PYTHON_DOWNLOADS=never
            uv sync
          '';

          postShellHook = ''
            unset SOURCE_DATE_EPOCH
            export UV_PYTHON_DOWNLOADS=never
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc
              pkgs.zlib
            ]}
            echo "Anemone environment loaded"
            echo "Python: $(python --version)"
            echo "uv: $(uv --version)"
            echo "Node: $(node --version)"
          '';
        };
      }
    );
}
