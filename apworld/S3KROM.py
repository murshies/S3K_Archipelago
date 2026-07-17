import importlib
import os
import pathlib

import settings
import Utils
from worlds.AutoWorld import World
from worlds.Files import APProcedurePatch, APTokenMixin

from . import consts

BASE_PATCH_FILE_NAME = "base_patch.bsdiff4"
BASE_ROM_MD5 = "c5b1c655c19f462ade0ac4e17a844d10"


class S3KProcedurePatch(APProcedurePatch, APTokenMixin):
    game = consts.GAME
    hash = BASE_ROM_MD5
    patch_file_ending = ".aps3k"
    result_file_ending = ".md"
    procedure = [
        ("apply_bsdiff4", [BASE_PATCH_FILE_NAME])
    ]

    @classmethod
    def get_source_data(cls) -> bytes:
        base_rom_file_name = settings.get_settings().s3k_settings["rom_file"]
        if not os.path.exists(base_rom_file_name):
            base_rom_file_name = Utils.user_path(base_rom_file_name)
        with open(base_rom_file_name, "rb") as f:
            base_rom_bytes = f.read()
        return base_rom_bytes


class S3KSettings(settings.Group):
    class S3KROMFile(settings.UserFilePath):
        """The file name of the Sonic 3 & Knuckles Base ROM"""
        required = True
        description = "Sonic 3 & Knuckles ROM file"
        copy_to = "Sonic & Knuckles + Sonic The Hedgehog 3 (USA).md"
        md5s = [BASE_ROM_MD5]

    rom_file: S3KROMFile = S3KROMFile(S3KROMFile.copy_to)


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
