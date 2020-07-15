import logging
import os
import yaml
import typing

from ...directory import agent_directory
from ..step import Step

if typing.TYPE_CHECKING:
    from ...agent import Agent


logger = logging.getLogger("datatorch.agent.job")


class Job(object):
    def __init__(self, config: dict, agent: "Agent" = None):
        self.config = config
        self.agent = agent

        self.id = self.config.get("id")
        self.dir = agent_directory.task_dir(self.id) if self.id else "./"

        if self.id:
            path = os.path.join(self.dir, "job.yaml")
            with open(path, "w") as yaml_config:
                yaml.dump(self.config, yaml_config, default_flow_style=False)

    async def update(self, status: str) -> None:
        if self.agent is None:
            return None
        variables = {"id": self.id, "status": status}
        await self.agent.api.update_job(variables)

    async def run(self):
        """ Runs each step of the job. """
        steps = Step.from_dict_list(self.config.get("steps", []), job=self)
        inputs = {}
        await self.update("RUNNING")

        for step in steps:
            try:
                inputs = {**inputs, **await step.run(inputs)}
            except Exception as e:
                logger.error(f"Job {self.config.get('name')} {self.id} failed: {e}")
                step.log(f"Step failed {e}.")
                await step.upload_logs()
                await step.update(status="FAILED")
                break

        else:
            await self.update("SUCCESS")
            logger.info("Successfully completed job.")
            return

        await self.update("FAILED")

    @property
    def api(self):
        return self.agent and self.agent.api
