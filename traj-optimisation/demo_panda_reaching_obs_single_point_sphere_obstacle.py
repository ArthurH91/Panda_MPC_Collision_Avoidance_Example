from os.path import dirname, join, abspath
import time
import numpy as np

import pinocchio as pin
import hppfcl

from wrapper_meshcat import MeshcatWrapper
from wrapper_robot import RobotWrapper
from ocp_panda_reaching import OCPPandaReaching
from ocp_panda_reaching_obs_single_point import OCPPandaReachingColWithSingleCol

from utils import BLUE, YELLOW_FULL, GREEN, GREEN_FULL, RED, RED_FULL,BLACK

### PARAMETERS
# Number of nodes of the trajectory
T = 200
# Time step between each node
dt = 0.001


### LOADING THE ROBOT
pinocchio_model_dir = join(dirname(dirname(str(abspath(__file__)))), "models")
model_path = join(pinocchio_model_dir, "franka_description/robots")
mesh_dir = pinocchio_model_dir
urdf_filename = "franka2.urdf"
urdf_model_path = join(join(model_path, "panda"), urdf_filename)
srdf_model_path = model_path + "/panda/demo.srdf"

# Creating the robot
robot_wrapper = RobotWrapper(
    urdf_model_path=urdf_model_path, mesh_dir=mesh_dir, srdf_model_path=srdf_model_path
)
rmodel, cmodel, vmodel = robot_wrapper()
rdata = rmodel.createData()
cdata = cmodel.createData()

### CREATING THE TARGET
# TARGET_POSE = pin.SE3(pin.utils.rotate("x", np.pi), np.array([0, 0, 0.85]))
# TARGET_POSE.translation = np.array([0, -0.4, 1.5])

TARGET_POSE = pin.SE3(pin.utils.rotate("x", np.pi), np.array([0, -0.0, 0.85]))

OBSTACLE_POSE = pin.SE3(pin.utils.rotate("x", np.pi), np.array([0, -0.2, 1.2]))
OBSTACLE_RADIUS = 0.5e-1

### CREATING THE OBSTACLE
# OBSTACLE_RADIUS = 1.5e-1
# OBSTACLE_POSE = pin.SE3.Identity()
# OBSTACLE_POSE.translation = np.array([0.25, -0.425, 1.5])
# OBSTACLE = hppfcl.Capsule(0.1,0.1)
OBSTACLE = hppfcl.Sphere(OBSTACLE_RADIUS*2)
OBSTACLE_GEOM_OBJECT = pin.GeometryObject(
    "obstacle",
    rmodel.getFrameId("universe"),
    rmodel.frames[rmodel.getFrameId("universe")].parent,
    OBSTACLE,
    OBSTACLE_POSE,
)
OBSTACLE_GEOM_OBJECT.meshColor = BLUE

IG_OBSTACLE = cmodel.addGeometryObject(OBSTACLE_GEOM_OBJECT)

### INITIAL CONFIG OF THE ROBOT
INITIAL_CONFIG = pin.neutral(rmodel)

### ADDING THE COLLISION PAIR BETWEEN A LINK OF THE ROBOT & THE OBSTACLE
cmodel.geometryObjects[cmodel.getGeometryId("panda2_link7_sc_4")].meshColor = GREEN_FULL
cmodel.geometryObjects[cmodel.getGeometryId("panda2_link7_sc_1")].meshColor = GREEN_FULL
cmodel.geometryObjects[cmodel.getGeometryId("panda2_link6_sc_2")].meshColor = GREEN_FULL
cmodel.geometryObjects[cmodel.getGeometryId("panda2_link5_sc_3")].meshColor = GREEN_FULL

cmodel.geometryObjects[cmodel.getGeometryId("panda2_link5_sc_4")].meshColor = BLACK


cmodel.addCollisionPair(
    pin.CollisionPair(cmodel.getGeometryId("panda2_link7_sc_1"), IG_OBSTACLE)
)
cdata = cmodel.createData()
print(f'shape 1 : {cmodel.getGeometryId("panda2_link6_sc_2")}')
print(f'shape 2 : {IG_OBSTACLE}')

for i in range(len(cmodel.geometryObjects)):
    print(cmodel.geometryObjects[i].name)

# Generating the meshcat visualizer
MeshcatVis = MeshcatWrapper()
vis, meshcatVis = MeshcatVis.visualize(
    TARGET_POSE,
    robot_model=rmodel,
    robot_collision_model=cmodel,
    robot_visual_model=vmodel,
)
input()
### INITIAL X0
q0 = INITIAL_CONFIG
q0 = np.array([ 0.439,   0.9274 , 0.3113 , 0.3734 ,-0.2116,  1.1214 , 0.024])
x0 = np.concatenate([q0, pin.utils.zero(rmodel.nv)])

### CREATING THE PROBLEM WITHOUT OBSTACLE
problem = OCPPandaReaching(
    rmodel,
    cmodel,
    TARGET_POSE,
    T,
    dt,
    x0,
    WEIGHT_GRIPPER_POSE=100,
    WEIGHT_xREG=1e-2,
    WEIGHT_uREG=1e-4,
)
ddp = problem()
# Solving the problem
ddp.solve()

XS_init = ddp.xs
US_init = ddp.us
print(XS_init)
vis.display(q0)
input()
for xs in ddp.xs:
    vis.display(np.array(xs[:7].tolist()))
    time.sleep(1e-3)

print("Start of the OCP with obstacle constraint")
### CREATING THE PROBLEM WITH WARM START
problem = OCPPandaReachingColWithSingleCol(
    rmodel,
    cmodel,
    TARGET_POSE,
    OBSTACLE_POSE,
    OBSTACLE_RADIUS,
    T,
    dt,
    x0,
    WEIGHT_GRIPPER_POSE=100,
    WEIGHT_xREG=1e-2,
    WEIGHT_uREG=1e-4,
    SAFETY_THRESHOLD=5e-3
)
print("creating the ocp")
ddp = problem()
# ddp.solve()

print("solving the ocp")
# Solving the problem
ddp.solve(XS_init, US_init)
input()
print("End of the computation, press enter to display the traj if requested.")
### DISPLAYING THE TRAJ
while True:
    for xs in ddp.xs:
        vis.display(np.array(xs[:7].tolist()))
        time.sleep(1e-3)
    print("replay")
