#!/usr/bin/env python3
# Copyright 2024 Weii Wang
# See LICENSE file for licensing details.

"""Flask Charm entrypoint."""
import json
import logging
import typing

import ops

import xiilib.flask
from xiilib.exceptions import CharmConfigInvalidError

logger = logging.getLogger(__name__)


class FlaskCharm(xiilib.flask.Charm):
    """Flask Charm service."""

    _RELATION_NAME = "amqp"

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.framework.observe(
            self.on[self._RELATION_NAME].relation_changed,
            self._on_rabbitmq_relation_changed,
        )
        self.framework.observe(
            self.on[self._RELATION_NAME].relation_broken,
            self._on_rabbitmq_relation_broken,
        )

    def _on_rabbitmq_relation_changed(self, _event: ops.RelationEvent):
        """Handle the rabbitmq relation changed event."""
        relations = self.model.relations[self._RELATION_NAME]
        for relation in relations:
            if relation.app is None:
                continue
            data = relation.data[self.app]
            data["vhost"] = self.config.get("vhost")
            data["username"] = self.app.name
            data["admin"] = "true"
        self.restart_flask()

    def _on_rabbitmq_relation_broken(self, _event: ops.RelationEvent):
        """Handle the rabbitmq relation broken event."""
        self.restart_flask()

    def _get_rabbitmq_environment(self) -> typing.Dict[str, str]:
        """Generate the rabbitmq environment FLASK_RABBITMQ_URIS."""
        uris = {}
        relations = self.model.relations[self._RELATION_NAME]
        for relation in relations:
            if relation.app is None:
                continue
            for unit in relation.units:
                data = relation.data[unit]
                vhost = self.config.get("vhost")
                username = self.app.name
                hostname = data.get("hostname")
                if hostname is None:
                    continue
                password = data.get("password")
                if password is None:
                    continue
                uri = f"amqp://{username}:{password}@{hostname}/{vhost if vhost != '/' else ''}"
                uris[unit.name] = uri
        logger.info("retrieved rabbitmq uris: %s", uris)
        return {"FLASK_RABBITMQ_URIS": json.dumps(uris)}

    def restart_flask(self) -> None:
        """Restart the Flask application inside the container."""
        try:
            self._flask_app.restart(self._get_rabbitmq_environment())
            self._update_app_and_unit_status(ops.ActiveStatus())
        except CharmConfigInvalidError as exc:
            self._update_app_and_unit_status(ops.BlockedStatus(exc.msg))


if __name__ == "__main__":
    ops.main.main(FlaskCharm)
