from volttron.platform.vip.agent import Agent
from volttron.platform.agent import utils

utils.setup_logging()
a = Agent(identity="cli.turn_on")
a.core.start()

res = a.vip.rpc.call(
    "platform.driver",
    "set_point",
    "devices/building/room/light.bed_light",
    "light_state",
    1
).get(timeout=30)

print("TURN ON RESULT:", res)
a.core.stop()
