"""inspect all images"""
import json
import re

from typing import List
from typing import Tuple

from ..command_runner import Command
from ..command_runner import CommandRunner
from ..utils.functions import pascal_to_snake


class ImagesInspect:
    """inspect images"""

    def __init__(self, container_engine, ids):
        """Initialize the container image inspector.

        :param container_engine: The name of the container engine to use
        :param ids: The ids of the container images to inspect
        """
        self._container_engine = container_engine
        self._image_ids = ids

    @property
    def commands(self) -> List[Command]:
        """generate commands"""
        return [
            Command(
                identity=image_id,
                command=f"{self._container_engine} inspect {image_id}",
                post_process=self.parse,
            )
            for image_id in self._image_ids
        ]

    @staticmethod
    def parse(command: Command):
        """parse the output"""
        obj = json.loads(command.stdout)
        snake = pascal_to_snake(obj[0])
        command.details = snake


class ImagesList:
    """list the images"""

    def __init__(self, container_engine):
        """Initialize the container image lister.

        :param container_engine: The name of the container engine to use
        """
        self._container_engine = container_engine

    @property
    def commands(self) -> List[Command]:
        """generate command"""
        return [
            Command(
                identity="images",
                command=f"{self._container_engine} images",
                post_process=self.parse,
            ),
        ]

    @staticmethod
    def parse(command: Command):
        """parse the output"""
        if command.stdout:
            images = command.stdout.splitlines()
            re_2omo = re.compile(r"\s{2,}")
            headers = [key.lower().replace(" ", "_") for key in re_2omo.split(images.pop(0))]
            local_images = [dict(zip(headers, re_2omo.split(line))) for line in images]
            valid_images = [image for image in local_images if image["tag"] != "<none>"]
            command.details = valid_images


def inspect_all(container_engine: str) -> Tuple[List, str]:
    """run inspect against all images"""
    cmd_runner = CommandRunner()
    images_list_class = ImagesList(container_engine=container_engine)
    result = cmd_runner.run_single_proccess(commands=images_list_class.commands)
    images_list = result[0]
    if images_list.errors:
        return [], images_list.errors
    if images_list.stderr and not images_list.details:
        return [], images_list.stderr
    images = {image["image_id"]: image for image in images_list.details}
    image_ids = [image["image_id"] for image in images.values()]
    images_inspect_class = ImagesInspect(container_engine=container_engine, ids=image_ids)
    inspects = cmd_runner.run_single_proccess(commands=images_inspect_class.commands)
    for inspect in inspects:
        images[inspect.identity]["inspect"] = {"details": inspect.details, "errors": inspect.errors}
    return list(images.values()), images_list.stderr
