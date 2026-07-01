import importlib
import pathlib

from worlds.AutoWorld import World
from worlds.Files import APProcedurePatch, APTokenMixin

from . import consts

BASE_PATCH_FILE_NAME = "base_patch.bsdiff4"


class S3KProcedurePatch(APProcedurePatch, APTokenMixin):
    game = consts.GAME
    hash = "c5b1c655c19f462ade0ac4e17a844d10"
    patch_file_ending = ".aps3k"
    result_file_ending = ".md"
    procedure = [
        ("apply_bsdiff4", [BASE_PATCH_FILE_NAME])
    ]


def generate_output(world: World, output_directory: str) -> None:
    patch = S3KProcedurePatch(player=world.player, player_name=world.player_name)
    base_patch_file_path = importlib.resources.files(__name__) / BASE_PATCH_FILE_NAME
    with importlib.resources.as_file(base_patch_file_path) as file_name:
        with open(file_name, "rb") as f:
            base_patch = f.read()
    patch.write_file(BASE_PATCH_FILE_NAME, base_patch)

    # Generate the final patch file
    player_file_name_base = world.multiworld.get_out_file_name_base(world.player)
    player_file_name = f"{player_file_name_base}{patch.patch_file_ending}"
    patch.write(str(pathlib.Path(output_directory) / player_file_name))
