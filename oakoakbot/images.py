import os

SPRITES_FOLDER = os.environ.get("IMAGES_PATH", "data/images")


def load_pokemon_images(number, form, region, is_shiny, is_mega, gender) -> tuple:
    shiny_flag = "s" if is_shiny else "n"
    mega_flag = "m" if is_mega else "n"

    # Get colour image
    filename = f"{number:04}_{form:02}_{region}_{shiny_flag}_{mega_flag}_{gender}.jpg"
    with open(os.path.join(SPRITES_FOLDER, "colour", filename), "rb") as image:
        file = image.read()
        colour_image = bytearray(file)

    # Get silhouette image
    filename = f"{number:04}_{form:02}_{region}_{mega_flag}_{gender}.jpg"
    with open(os.path.join(SPRITES_FOLDER, "silhouettes", filename), "rb") as image:
        file = image.read()
        silhouette_image = bytearray(file)

    return colour_image, silhouette_image
