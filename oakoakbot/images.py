import io
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_IMAGE = "data/images/misc/background_image.jpg"
POKEMON_LOGO = "data/images/misc/pokemon_logo.png"
QUESTION_MARK = "data/images/misc/question_mark.png"

COLOURS = {
    "blue": (22, 104, 151, 255),
    "darker_blue": (28, 69, 90, 180),
    "shadow": (72, 86, 112, 135),
    "yellow": (252, 202, 49, 255),
    "black": (0, 0, 0, 255),
}
SHADOW_OFFSET = (15, 12)
CONTOUR_OFFSET = (20, 15)


def silhouette_from_image(image, rgba):
    mask = (np.array(image)[..., 3] > 0).astype(np.uint8)
    return Image.fromarray(np.stack([colour * mask for colour in rgba], 2))


def paste_image_with_shadow(base_image, image, position):
    shadow = silhouette_from_image(image, COLOURS["shadow"])
    blue_contour = silhouette_from_image(image, COLOURS["darker_blue"])

    base_image.paste(shadow, position, shadow)
    base_image.paste(
        blue_contour,
        (position[0] + SHADOW_OFFSET[0], position[1] - SHADOW_OFFSET[1]),
        blue_contour,
    )
    base_image.paste(
        image, (position[0] + CONTOUR_OFFSET[0], position[1] - CONTOUR_OFFSET[1]), image
    )


async def create_pokemon_image(pokemon_image, pokemon_name, is_silhouette):
    # Load base image
    base_image = Image.open(BASE_IMAGE).convert("RGB")

    # Create pokemon image or silhouette with shadows
    pokemon_image = Image.open(pokemon_image).convert("RGBA")
    pokemon_image = pokemon_image.crop(pokemon_image.getbbox())
    if is_silhouette:
        pokemon_image = silhouette_from_image(pokemon_image, COLOURS["blue"])

    # Calculate pokemon position
    w_start = max(10, math.ceil(base_image.size[0] * 0.25 - pokemon_image.size[0] / 2))
    h_start = max(10, math.ceil(base_image.size[1] * 0.4 - pokemon_image.size[1] / 2))

    # Paste the pokemon image into the background
    paste_image_with_shadow(base_image, pokemon_image, (w_start, h_start))

    # Paste pokemon logo
    pokemon_logo = Image.open(POKEMON_LOGO).convert("RGBA")
    pokemon_logo.thumbnail(
        [math.ceil(dim * 0.5) for dim in pokemon_logo.size]
    )  # remove this
    pokemon_logo = pokemon_logo.crop(pokemon_logo.getbbox())
    paste_image_with_shadow(
        base_image,
        pokemon_logo,
        (math.ceil(base_image.size[0] * 0.45), math.ceil(base_image.size[1] * 0.6)),
    )

    if is_silhouette:
        # Paste pokemon logo
        question_mark = Image.open(QUESTION_MARK).convert("RGBA")
        question_mark.thumbnail(
            [math.ceil(dim * 0.75) for dim in question_mark.size]
        )  # remove this
        question_mark = question_mark.crop(question_mark.getbbox())
        paste_image_with_shadow(
            base_image,
            question_mark,
            (
                math.ceil(base_image.size[0] * 0.6),
                math.ceil(base_image.size[1] * 0.15),
            ),
        )
    else:
        # Paste pokemon font
        text_image = Image.new("RGBA", (800, 300), (255, 255, 255, 0))
        contour_image = Image.new("RGBA", (800, 300), (255, 255, 255, 0))

        font = ImageFont.truetype("data/fonts/Playhouse Medium.ttf", 100)
        text_pos = (400, 150)

        draw = ImageDraw.Draw(text_image)
        draw.text(
            text_pos,
            pokemon_name.upper(),
            fill=COLOURS["blue"],
            font=font,
            anchor="mm",
            stroke_width=7,
            stroke_fill=COLOURS["black"],
        )

        draw = ImageDraw.Draw(contour_image)
        draw.text(
            text_pos,
            pokemon_name.upper(),
            fill=(0, 0, 0, 0),
            font=font,
            anchor="mm",
            stroke_width=5,
            stroke_fill=COLOURS["yellow"],
        )
        # text_image.show()
        text_image = Image.alpha_composite(text_image, contour_image)
        text_image.crop(text_image.getbbox())
        paste_image_with_shadow(
            base_image,
            text_image,
            (
                math.ceil(base_image.size[0] * 0.71 - text_image.size[0] * 0.5),
                math.ceil(base_image.size[1] * 0.33 - text_image.size[1] * 0.5),
            ),
        )

    # Resize the image to increase response time (make this parameterizable)
    base_image.thumbnail([math.ceil(dim * 0.6) for dim in base_image.size])

    # Save it to bytes buffer
    with io.BytesIO() as output:
        base_image.save(output, format="GIF")
        bytes_image = output.getvalue()

    return bytes_image
