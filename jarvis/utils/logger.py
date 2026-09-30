import logging

def configure_logging(level: str = "INFO", debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
