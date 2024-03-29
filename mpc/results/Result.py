from os.path import dirname, abspath
import json, codecs

import numpy as np
import pinocchio as pin
import hppfcl

class Result():
    "This class processes the results of a MPC simulation"
    
    def __init__(self, path : str) -> None:
        """Instaciate the class with the path of the json file

        Args:
            path (str): path of the json file
        """

        self._path = path
        json_file = codecs.open(
                self._path, "r", encoding="utf-8"
        ).read()
        # Loading the json file
        self._results = json.loads(json_file)
        self._nq = 7
        self._nx = 14

    def get_name(self):
        
        name_split = self._path.split("/")
        self._name = name_split[-1][:-5]
        return self._name
    
    def get_weights(self):
        """Returns the list of weights in the following order : 
        [WEIGHT_GRIPPER_POSE,WEIGHT_GRIPPER_POSE_TERM,WEIGHT_xREG,WEIGHT_xREG_TERM,WEIGHT_uREG]

        Returns:
            list: list of the weights
        """
        return self._results["weights"]

    def get_max_iter(self):
        """Returns the max iter of the solver. Be careful not to misunderstand the difference between
        max_iter & max_qp_iters. max_iter is the number of iterations maximum of the solver. max_qp_iters 
        is the number of iterations maximum of the qp solved in each iteration of the solver.

        Returns:
            int: max_iter
        """
        return self._results["max_iter"]
    
    def get_max_qp_iters(self):
        """Returns the max qp iter of the each iteration of the solver solver. Be careful not to misunderstand the difference between
        max_iter & max_qp_iters. max_iter is the number of iterations maximum of the solver. max_qp_iters 
        is the number of iterations maximum of the qp solved in each iteration of the solver.

        Returns:
            int: max_qp_iters
        """
        return self._results["max_qp_iters"]
    def get_time_calc(self):
        """Returns the time it took for each resolution of the solver. The time is in seconds.
        
        Returns:
            list : time_calc
        """
        return self._results["time_calc"]
    
    def get_Nnodes(self):
        """Returns the number of nodes used for the MPC.
        
        Returns:
            int: Nnodes
        """
        return self._results["Nnodes"]
    
    def get_dt(self):
        """Returns the dt of the MPC.
        
        Returns:
            int: dt
        """
        return self._results["dt"]
    
    def get_collision_pairs(self):
        """Returns the list of the collision pairs. Needs to call the robot load the know which pair correspond to 
        which collision shape. 

        Returns:
            list: list_coll_pairs
        """
        return self._results["collision_pairs"]
    
    def get_X(self):
        """Returns the list of states (configuration, velocity) of each joints at each time step.

        Returns:
            list: X
        """
        X_raw = np.array(self._results["X"])
        X_processed = np.split(X_raw, int(len(X_raw) / self._nx))
        self._Q = []
        self._V = []
        for x in X_processed:
            self._Q.append(x[:self._nq])
            self._V.append(x[self._nq:])
        return X_processed

    def get_U(self):
        """Returns the list of control (torque) of each joints at each time step. """
        
        return np.array(self._results["U"])
    
    def get_Q(self):
        """Return the list of configurations of each joints at each time step."""
        
        self.get_X()
        return np.array(self._Q)
    
    def get_V(self):
        """Return the list of velocities of each joints at each time step."""
        
        self.get_X()
        return np.array(self._V)
    
    def compute_minimal_distances_between_collision_pairs(self, rmodel, cmodel):
        """Returns a dictionnary containing the minimal distances to the obstacle.

        Args:
            rmodel (pin.Model): Pinocchio joints model of the robot.
            cmodel (pin.GeometryModel): Pinocchio collision model of the robot.

        Returns:
            dict: minimal distances to the obstacle.
        """
        rdata = rmodel.createData()
        cdata = cmodel.createData()
        req = hppfcl.DistanceRequest()
        res = hppfcl.DistanceResult()
        col_pairs = self.get_collision_pairs()
        dist_min_for_each_pair = {}
        Q = self.get_Q()
        for pair in col_pairs:
            shape1_id = pair[0]
            shape2_id = pair[1]
            dist_min_for_each_pair[cmodel.geometryObjects[shape1_id].name + "-" + cmodel.geometryObjects[shape2_id].name] = []
            for q in Q:
                pin.framesForwardKinematics(rmodel, rdata, q)
                pin.updateGeometryPlacements(
                    rmodel, rdata, cmodel, cdata, q
                )
                T1 = cdata.oMg[shape1_id]
                T2 = cdata.oMg[shape2_id]
                dist = hppfcl.distance(
                    cmodel.geometryObjects[shape1_id].geometry,
                    T1,
                    cmodel.geometryObjects[shape1_id].geometry,
                    T2,
                    req,
                    res)
                dist_min_for_each_pair[cmodel.geometryObjects[shape1_id].name + "-" + cmodel.geometryObjects[shape2_id].name].append(dist)
                
        return dist_min_for_each_pair

    def compute_distances_between_target1_scene1(self, rmodel):
        """Returns a dictionnary containing the minimal distances to the obstacle.

        Args:
            rmodel (pin.Model): Pinocchio joints model of the robot.
            cmodel (pin.GeometryModel): Pinocchio collision model of the robot.

        Returns:
            dict: minimal distances to the obstacle.
        """
        rdata = rmodel.createData()
        dist_min_target1 = []
        Q = self.get_Q()
        frame1_id = rmodel.getFrameId("panda2_rightfinger")
        TARGET_POSE1 = pin.SE3(pin.utils.rotate("x", np.pi), np.array([0, -0.4, 1.5]))
        for q in Q:
            pin.framesForwardKinematics(rmodel, rdata, q)
            T1 = rdata.oMf[frame1_id]
            dist_min_target1.append( np.linalg.norm((T1.translation - TARGET_POSE1.translation)))
        return dist_min_target1

    def compute_distances_between_target2_scene1(self, rmodel):
        """Returns a dictionnary containing the minimal distances to the obstacle.

        Args:
            rmodel (pin.Model): Pinocchio joints model of the robot.
            cmodel (pin.GeometryModel): Pinocchio collision model of the robot.

        Returns:
            dict: minimal distances to the obstacle.
        """
        rdata = rmodel.createData()
        dist_min_target2 = []
        Q = self.get_Q()
        frame1_id = rmodel.getFrameId("panda2_rightfinger")
        TARGET_POSE2 = pin.SE3(pin.utils.rotate("x", np.pi), np.array([0, -0.0, 1.5]))
        for q in Q:
            pin.framesForwardKinematics(rmodel, rdata, q)
            T1 = rdata.oMf[frame1_id]
            dist_min_target2.append( np.linalg.norm((T1.translation - TARGET_POSE2.translation)))
      
        return dist_min_target2
if __name__=="__main__":
    
    curr_path = dirname(str(abspath(__file__)))

    test = Result(curr_path + "/scene1/comparingnodes/nnodes10fdt50maxit10maxqpiters25.json")
    test._results["weights"]
    print(test._results["weights"])
    
    print(test.get_name())