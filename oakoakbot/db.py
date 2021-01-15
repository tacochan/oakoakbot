import csv
import datetime
import glob
import os
import random
import time

from peewee import (
    fn,
    SqliteDatabase,
    Model,
    IntegerField,
    CharField,
    FloatField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
)

from oakoakbot.logger import get_logger

DEFAULT_SPAWN_RATE = 1 / 133
SHINY_CHANCE = 0.01  # This should be relative to group chance
NUM_GENERATIONS = 8

POKEMON_CSV = "data/pokemon.csv"
DB_FILE = "data/oak_db.sqlite3"
SPRITES_FOLDER = "data/images/pokemon"


logger = get_logger()

db = SqliteDatabase(DB_FILE)
registered_groups = []


class WildEncounter:
    def __init__(self, pokemon, include_alolan=False, include_galarian=False):
        self.pokemon = pokemon
        self.release_time = time.time()
        self.shiny = False
        if random.random() < SHINY_CHANCE:
            self.shiny = True

        shiny_flag = "r" if self.shiny else "n"
        filename = f"poke_capture_{pokemon.number:04}*_{shiny_flag}.png"

        sprites = glob.glob(os.path.join(SPRITES_FOLDER, filename))

        # Exclude mega evolution sprites
        sprites = [sprite for sprite in sprites if "_m_" not in sprite]

        # Exclude alolan and galarian forms if specified
        if include_alolan is False:
            sprites = [sprite for sprite in sprites if "_a_" not in sprite]
        if include_galarian is False:
            sprites = [sprite for sprite in sprites if "_g_" not in sprite]

        self.sprite_filename = sprites[random.randint(0, len(sprites) - 1)]

        attributes = self.sprite_filename.split("_")
        self.form = attributes[3]
        self.gender = attributes[4]
        self.region = attributes[5]


class CustomModel(Model):
    class Meta:
        database = db


class Pokemon(CustomModel):
    number = IntegerField()
    name = CharField()
    form = IntegerField(default=1)
    region = CharField(default="global")
    type_1 = CharField()
    type_2 = CharField()
    ability_1 = CharField()
    ability_2 = CharField()
    ability_hidden = CharField()
    generation = IntegerField()
    legendary = BooleanField()
    mega = BooleanField()
    height = FloatField()
    weight = FloatField()
    hp = IntegerField()
    attack = IntegerField()
    defense = IntegerField()
    special_attack = IntegerField()
    special_defense = IntegerField()
    speed = IntegerField()
    total = IntegerField()

    @staticmethod
    def init_table_from_csv(csv_filename):
        with open(csv_filename, "r") as csv_file:
            rows = csv.DictReader(csv_file)
            pokemon_to_add = [
                Pokemon(
                    number=r["NUMBER"],
                    name=r["NAME"],
                    type_1=r["TYPE1"],
                    type_2=r["TYPE2"],
                    ability_1=r["ABILITY1"],
                    ability_2=r["ABILITY2"],
                    ability_hidden=r["ABILITY HIDDEN"],
                    generation=r["GENERATION"],
                    legendary=int(r["LEGENDARY"]),
                    mega=int(r["MEGA_EVOLUTION"]),
                    height=r["HEIGHT"],
                    weight=r["WEIGHT"],
                    hp=r["HP"],
                    attack=r["ATK"],
                    defense=r["DEF"],
                    special_attack=r["SP_ATK"],
                    special_defense=r["SP_DEF"],
                    speed=r["SPD"],
                    total=r["TOTAL"],
                )
                for r in rows
            ]

            Pokemon.bulk_create(pokemon_to_add)

    @staticmethod
    def get_random_encounter(group_id) -> WildEncounter:
        t0 = time.time()
        generations = GroupsConfiguration.get_generations(group_id)
        pokemon = (
            Pokemon.select()
            .where(Pokemon.generation.in_(generations) & (Pokemon.mega == 0))
            .order_by(fn.Random())
            .limit(1)
            .execute()
        )[0]
        logger.info(f"Pokemon fetched in {time.time() - t0:02}")
        return WildEncounter(pokemon)


class PokemonNatures(CustomModel):
    name = CharField()
    increases = CharField()
    decreases = CharField()


class GroupsConfiguration(CustomModel):
    group_id = IntegerField(unique=True)
    pokemon_rate = FloatField(default=DEFAULT_SPAWN_RATE)
    generations = CharField(default=list(range(1, NUM_GENERATIONS + 1)))

    @staticmethod
    def add_group(group_id):
        GroupsConfiguration.create(group_id=group_id)

    @staticmethod
    def get_groups():
        groups = GroupsConfiguration.select(GroupsConfiguration.group_id).execute()
        return [group.group_id for group in groups]

    @staticmethod
    def set_pokemon_rate(group_id, pokemon_rate):
        updated_rows = (
            GroupsConfiguration.update(pokemon_rate=pokemon_rate)
            .where(GroupsConfiguration.group_id == group_id)
            .execute()
        )
        return updated_rows == 1

    @staticmethod
    def get_pokemon_rate(group_id):
        return (
            GroupsConfiguration.select(GroupsConfiguration.pokemon_rate)
            .where(group_id == group_id)
            .execute()
        )[0].pokemon_rate

    @staticmethod
    def set_generations(group_id, generations):
        generations_serialized = ",".join(str(gen) for gen in generations)
        updated_rows = (
            GroupsConfiguration.update(generations=generations_serialized)
            .where(GroupsConfiguration.group_id == group_id)
            .execute()
        )
        return updated_rows == 1

    @staticmethod
    def get_generations(group_id):
        generations = (
            GroupsConfiguration.select(GroupsConfiguration.generations)
            .where(group_id == group_id)
            .execute()
        )[0].generations
        return [int(gen) for gen in generations.split(",")]


class Teams(CustomModel):
    user_id = CharField()
    group_id = CharField()


class CaughtPokemon(CustomModel):
    team_id = ForeignKeyField(Teams)
    pokemon_id = ForeignKeyField(Pokemon)
    catch_date = DateTimeField(default=datetime.datetime.now)
    level = IntegerField(default=1)
    shiny = BooleanField()
    gender = CharField()
    ability = CharField()
    nature = CharField()
    hp_iv = IntegerField()
    attack_iv = IntegerField()
    defense_iv = IntegerField()
    special_attack_iv = IntegerField()
    special_defense_iv = IntegerField()
    speed_iv = IntegerField()


db.connect()
db.create_tables([Pokemon, PokemonNatures, Teams, GroupsConfiguration, CaughtPokemon])
registered_groups = GroupsConfiguration.get_groups()
