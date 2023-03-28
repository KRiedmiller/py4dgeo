import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
from sklearn.utils.multiclass import unique_labels

# from sklearn.metrics import euclidean_distances

from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.compose import ColumnTransformer
from sklearn.compose import make_column_selector

from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import cross_val_score

from sklearn.ensemble import RandomForestClassifier

from sklearn.utils.estimator_checks import check_estimator

from sklearn import set_config

set_config(display="diagram")

from abc import ABC, abstractmethod

from py4dgeo.epoch import *
from py4dgeo import *

from IPython import display

try:
    from vedo import *

    interactive_available = True
except ImportError:
    interactive_available = False

import colorsys

import random

__all__ = [
    "BaseTransformer",
    "AddLLSVandPCA",
    "Segmentation",
    "ExtractSegments",
    "BuildSimilarityFeature_and_y",
    "BuildSimilarityFeature_and_y_RandomPairs",
    "BuildSimilarityFeature_and_y_Visually",
    "SimplifiedClassifier",
    "ClassifierWrapper",
    "PB_M3C2",
    #    "_build_input_scenario2_without_normals",
    #    "_build_input_scenario2_with_normals",
    "PB_M3C2_with_segments",
    "set_interactive_backend",
    "generate_random_y",
]


def set_interactive_backend(backend="vtk"):
    """Set the interactive backend for selection of correspondent segements.

    All backends that can be used with the vedo library can be given here.
    E.g. the following backends are available: vtk, ipyvtk, k3d, 2d, ipygany, panel, itk
    """
    if interactive_available:
        from vedo import settings

        settings.default_backend = backend


def angle_difference_compute(normal1, normal2):

    """

    :param normal1:
    :param normal2:
    :return:
    """

    # normal1, normal2 have to be unit vectors ( and that is the case as a result of the SVD process )
    return np.arccos(np.clip(np.dot(normal1, normal2), -1.0, 1.0)) * 180.0 / np.pi


def geodesic_distance(v1, v2):

    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)

    return min(
        np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)) * 180.0 / np.pi,
        np.arccos(np.clip(np.dot(v1_u, -v2_u), -1.0, 1.0)) * 180.0 / np.pi,
    )


def HSVToRGB(h, s, v):

    """

    :param h:
    :param s:
    :param v:
    :return:
    """
    return colorsys.hsv_to_rgb(h, s, v)


def get_distinct_colors(n):

    """

    :param n:
    :return:
    """

    huePartition = 1.0 / (n + 1)
    return [HSVToRGB(huePartition * value, 1.0, 1.0) for value in range(0, n)]


def points_segmentation_visualizer(X):

    """

    :param X:
    :return:
    """

    sets = []

    max = int(X[:, 17].max())
    colors = get_distinct_colors(max + 1)

    plt = Plotter(axes=3)

    for i in range(0, max + 1):

        mask = X[:, 17] == float(i)
        set_cloud = X[mask, :3]  # x,y,z

        sets = sets + [Points(set_cloud, colors[i], alpha=1, r=10)]

    plt.show(sets).close()


def compute_similarity_between(seg_epoch0, seg_epoch1):

    """

    :param seg_epoch0: segment from epoch0
    :param seg_epoch1: segment from epoch1
    :return:
        angle, -> angle between plane normal vectors
        points_density_diff, -> difference between points density between pairs of segments
        eigen_value_smallest_diff, -> difference in the quality of plane fit (smallest eigenvalue)
        eigen_value_largest_diff, -> difference in plane extension (largest eigenvalue)
        eigen_value_middle_diff, -> difference in orthogonal plane extension (middle eigenvalue)
        nr_points_diff, -> difference in number of points per plane
    """

    X_Column = 0
    Y_Column = 1
    Z_Column = 2

    EpochID_Column = 3
    Eigenvalue0_Column = 4
    Eigenvalue1_Column = 5
    Eigenvalue2_Column = 6
    Eigenvector0x_Column = 7
    Eigenvector0y_Column = 8
    Eigenvector0z_Column = 9
    Eigenvector1x_Column = 10
    Eigenvector1y_Column = 11
    Eigenvector1z_Column = 12
    Eigenvector2x_Column = 13
    Eigenvector2y_Column = 14
    Eigenvector2z_Column = 15
    llsv_Column = 16
    Segment_ID_Column = 17

    Standard_deviation_Column = 18

    Nr_points_seg_Column = 19  # 18

    Normal_Columns = [Eigenvector2x_Column, Eigenvector2y_Column, Eigenvector2z_Column]

    # angle = np.arccos(
    #     np.clip(np.dot(seg_epoch0[Normal_Columns], seg_epoch1[Normal_Columns]), -1.0, 1.0)
    # ) * 180./np.pi
    angle = angle_difference_compute(
        seg_epoch0[Normal_Columns], seg_epoch1[Normal_Columns]
    )

    points_density_seg_epoch0 = seg_epoch0[Nr_points_seg_Column] / (
        seg_epoch0[Eigenvalue0_Column] * seg_epoch0[Eigenvalue1_Column]
    )

    points_density_seg_epoch1 = seg_epoch1[Nr_points_seg_Column] / (
        seg_epoch1[Eigenvalue0_Column] * seg_epoch1[Eigenvalue1_Column]
    )

    points_density_diff = abs(points_density_seg_epoch0 - points_density_seg_epoch1)

    eigen_value_smallest_diff = abs(
        seg_epoch0[Eigenvalue2_Column] - seg_epoch1[Eigenvalue2_Column]
    )
    eigen_value_largest_diff = abs(
        seg_epoch0[Eigenvalue0_Column] - seg_epoch1[Eigenvalue0_Column]
    )
    eigen_value_middle_diff = abs(
        seg_epoch0[Eigenvalue1_Column] - seg_epoch1[Eigenvalue1_Column]
    )

    nr_points_diff = abs(
        seg_epoch0[Nr_points_seg_Column] - seg_epoch1[Nr_points_seg_Column]
    )

    return np.array(
        [
            angle,
            points_density_diff,
            eigen_value_smallest_diff,
            eigen_value_largest_diff,
            eigen_value_middle_diff,
            nr_points_diff,
        ]
    )


sets = []
plt = None


def toggle_transparenct(evt):

    global sets
    global plt

    if evt.keyPressed == "z":
        print("transparency toggle")
        for segment in sets:
            if segment.alpha() < 1.0:
                segment.alpha(1)
            else:
                segment.alpha(0.5)
        plt.render()

    if evt.keyPressed == "g":
        print("toggle red")
        for segment in sets:
            if segment.epoch == 0:
                if segment.isOn == True:
                    segment.off()
                else:
                    segment.on()
                segment.isOn = not segment.isOn
        plt.render()

    if evt.keyPressed == "d":
        print("toggle green")
        for segment in sets:
            if segment.epoch == 1:
                if segment.isOn == True:
                    segment.off()
                else:
                    segment.on()
                segment.isOn = not segment.isOn
        plt.render()


def controller(evt):

    """

    :param evt:
    :return:
    """
    if not evt.actor:
        return  # no hit, return
    print("point coords =", evt.picked3d)
    if evt.isPoints:
        print(evt.actor)
    # print("full event dump:", evt)


def segments_visualizer(X):

    """

    :param X:
    :return:
    """

    X_Column = 0
    Y_Column = 1
    Z_Column = 2
    EpochID_Column = 3

    Eigenvalue0_Column = 4
    Eigenvalue1_Column = 5
    Eigenvalue2_Column = 6
    Eigenvector0x_Column = 7
    Eigenvector0y_Column = 8
    Eigenvector0z_Column = 9
    Eigenvector1x_Column = 10
    Eigenvector1y_Column = 11
    Eigenvector1z_Column = 12
    Eigenvector2x_Column = 13
    Eigenvector2y_Column = 14
    Eigenvector2z_Column = 15

    Segment_ID_Column = 17

    global sets
    sets = []

    max = X.shape[0]
    # colors = getDistinctColors(max)
    colors = [(1, 0, 0), (0, 1, 0)]

    global plt
    plt = Plotter(axes=3)

    plt.add_callback("EndInteraction", controller)
    # plt.add_callback('KeyRelease', toggle_transparenct)
    plt.add_callback("KeyPress", toggle_transparenct)

    for i in range(0, max):

        # mask = X[:, 17] == float(i)
        # set_cloud = X[mask, :3]  # x,y,z

        if X[i, EpochID_Column] == 0:
            color = colors[0]
        else:
            color = colors[1]

        # sets = sets + [Points(set_cloud, colors[i], alpha=1, r=10)]

        # sets = sets + [ Point( pos=(X[i, 0],X[i, 1],X[i, 2]), r=15, c=colors[i], alpha=1 ) ]
        ellipsoid = Ellipsoid(
            pos=(X[i, 0], X[i, 1], X[i, 2]),
            axis1=(
                X[i, Eigenvector0x_Column] * X[i, Eigenvalue0_Column] * 0.5,
                X[i, Eigenvector0y_Column] * X[i, Eigenvalue0_Column] * 0.5,
                X[i, Eigenvector0z_Column] * X[i, Eigenvalue0_Column] * 0.3,
            ),
            axis2=(
                X[i, Eigenvector1x_Column] * X[i, Eigenvalue1_Column] * 0.5,
                X[i, Eigenvector1y_Column] * X[i, Eigenvalue1_Column] * 0.5,
                X[i, Eigenvector1z_Column] * X[i, Eigenvalue1_Column] * 0.5,
            ),
            axis3=(
                X[i, Eigenvector2x_Column] * 0.1,
                X[i, Eigenvector2y_Column] * 0.1,
                X[i, Eigenvector2z_Column] * 0.1,
            ),
            res=24,
            c=color,
            alpha=1,
        )
        # ellipsoid.caption(txt=str(i), size=(0.1,0.05))
        ellipsoid.id = X[i, Segment_ID_Column]
        ellipsoid.epoch = X[i, EpochID_Column]
        ellipsoid.isOn = True
        # ellipsoid.on()
        sets = sets + [ellipsoid]

    plt.show(sets).close()


def generate_random_y(X, extended_y_file_name="locally_generated_extended_y.csv"):

    """
        Generate a subset (1/3 from the total possible pairs) of random tuples of segments ID
        (where each ID gets to be extracted from a different epoch) which are randomly labeled (0/1)
    :param X:
        (n, 20)
        Each row contains a segment.
    :param extended_y_file_name:
        Name of the file where the serialized result is saved.
    :return:
        numpy (m, 3)
            Where each row contains tuples of set0 segment id, set1 segment id, rand 0/1.
    """

    Segment_ID_Column = 17
    EpochID_Column = 3

    mask_epoch0 = X[:, EpochID_Column] == 0
    mask_epoch1 = X[:, EpochID_Column] == 1

    epoch0_set = X[mask_epoch0, :]  # all
    epoch1_set = X[mask_epoch1, :]  # all

    nr_pairs = min(epoch0_set.shape[0], epoch1_set.shape[0]) // 3

    indx0_seg_id = random.sample(range(epoch0_set.shape[0]), nr_pairs)
    indx1_seg_id = random.sample(range(epoch1_set.shape[0]), nr_pairs)

    set0_seg_id = epoch0_set[indx0_seg_id, Segment_ID_Column]
    set1_seg_id = epoch1_set[indx1_seg_id, Segment_ID_Column]

    rand_y_01 = list(np.random.randint(0, 2, nr_pairs))

    np.savetxt(
        extended_y_file_name,
        np.array([set0_seg_id, set1_seg_id, rand_y_01]).T,
        delimiter=",",
    )

    return np.array([set0_seg_id, set1_seg_id, rand_y_01]).T


class BaseTransformer(TransformerMixin, BaseEstimator, ABC):
    def __init__(self, skip=False):
        self.skip = skip
        super(BaseTransformer, self).__init__()

    @abstractmethod
    def _fit(self, X, y=None):
        """
        X : {array-like, sparse matrix}, shape (n_samples, n_features)
            The training input samples.
        y : None
            There is no need of a target in a transformer, yet the pipeline API
            requires this parameter.
        Returns
        -------
        self : object
            Returns self.
        """
        pass

    @abstractmethod
    def _transform(self, X):
        """
        X : {array-like, sparse-matrix}, shape (n_samples, n_features)
            The input samples.
        Returns
        -------
        X_transformed : array, shape (n_samples, n_features)
            The array containing the element-wise square roots of the values
            in ``X``.
        """
        pass

    def fit(self, X, y=None):

        if self.skip:
            return self

        X = check_array(X, accept_sparse=True)
        self.n_features_ = X.shape[1]

        # Return the transformer
        logger = logging.getLogger("py4dgeo")
        logger.info("Transformer Fit")
        return self._fit(X, y)

    def transform(self, X):

        if self.skip:
            return X

        # Check is fit had been called
        check_is_fitted(self, "n_features_")

        # Input validation
        X = check_array(X, accept_sparse=True)

        # Check that the input is of the same shape as the one passed
        # during fit.
        if X.shape[1] != self.n_features_:
            raise ValueError("Shape of input is different from what was seen in `fit`")

        logger = logging.getLogger("py4dgeo")
        logger.info("Transformer Transform")
        return self._transform(X)


class AddLLSVandPCA(BaseTransformer):
    def __init__(self, skip=False, radius=10):

        """

        :param skip: Whether the current transform is applied or not.
        :param radius: The radius used to extract the neighbour points using KD-tree.
        """

        super(AddLLSVandPCA, self).__init__(skip=skip)
        self.radius = radius

    def _llsv_and_pca(self, x, X):

        """
        Compute PCA (implicitly, the normal vector as well) and lowest local surface variation
        for point "x" using the set "X" as input.
        :param x:
        :param X:
        :return:
        """

        size = X.shape[0]

        # compute mean
        X_avg = np.mean(X, axis=0)
        B = X - np.tile(X_avg, (size, 1))

        # Find principal components (SVD)
        U, S, VT = np.linalg.svd(B.T / np.sqrt(size), full_matrices=0)

        # lowest local surface variation, normal vector
        # return np.hstack(( S[-1] / np.sum(S), U[:,2] ))

        x[-13:] = np.hstack(
            (
                S.reshape(1, -1),
                U[:, 0].reshape(1, -1),
                U[:, 1].reshape(1, -1),
                U[:, 2].reshape(1, -1),
                (S[-1] / np.sum(S)).reshape(1, -1),
            )
        )

        return x

    def _fit(self, X, y=None):
        """

        :param X:
        :param y:
        :return:
        """

        return self
        pass

    def _transform(self, X):

        """
        Extending X matrix with eigenvalues, eigenvectors, and lowest local surface variation columns.
        :param X: A numpy matrix with x,y,z,EpochID columns.
        :return:  X numpy matrix extended containing the following columns:
                x,y,z,EpochID columns and
                Eigenvalues( 3 columns )
                Eigenvectors( 3 columns ) X 3 [ in descending normal order ]
                Lowest local surface variation( 1 column )
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2
        EpochID_Column = 3
        X_Y_Z_Columns = [X_Column, Y_Column, Z_Column]

        mask_epoch0 = X[:, EpochID_Column] == 0
        mask_epoch1 = X[:, EpochID_Column] == 1

        epoch0_set = X[mask_epoch0, :-1]
        epoch1_set = X[mask_epoch1, :-1]

        _epoch = [Epoch(epoch0_set), Epoch(epoch1_set)]

        _epoch[0].build_kdtree()
        _epoch[1].build_kdtree()

        # add extra columns
        # Eigenvalues( 3 columns ) |
        # Eigenvectors( 3 columns ) X 3 [ in descending normal order ] |
        # Lowest local surface variation( 1 column )
        # Total 13 new columns
        new_columns = np.zeros((X.shape[0], 13))
        X = np.hstack((X, new_columns))

        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Normal_Columns = [
            Eigenvector2x_Column,
            Eigenvector2y_Column,
            Eigenvector2z_Column,
        ]

        return np.apply_along_axis(
            lambda x: self._llsv_and_pca(
                x,
                _epoch[int(x[EpochID_Column])].cloud[
                    _epoch[int(x[EpochID_Column])].kdtree.radius_search(
                        x[X_Y_Z_Columns], self.radius
                    )
                ],
            ),
            1,
            X,
        )
        # return X
        pass


class Segmentation(BaseTransformer):
    def __init__(
        self,
        skip=False,
        radius=2,
        angle_diff_threshold=1,
        disntance_3D_threshold=1.5,
        distance_orthogonal_threshold=1.5,
        llsv_threshold=1,
        roughness_threshold=5,
        max_nr_points_neighbourhood=100,
        min_nr_points_per_segment=5,
        with_previously_computed_segments=False,
    ):

        """

        :param skip:
        :param radius:
        :param angle_diff_threshold:
        :param disntance_3D_threshold:
        :param distance_orthogonal_threshold:
        :param llsv_threshold:
        :param roughness_threshold:
        :param max_nr_points_neighbourhood:
        :param min_nr_points_per_segment:
        :param with_previously_computed_segments:
        """

        super(Segmentation, self).__init__(skip=skip)

        self.radius = radius
        self.angle_diff_threshold = angle_diff_threshold
        self.disntance_3D_threshold = disntance_3D_threshold
        self.distance_orthogonal_threshold = distance_orthogonal_threshold
        self.llsv_threshold = llsv_threshold
        self.roughness_threshold = roughness_threshold
        self.max_nr_points_neighbourhood = max_nr_points_neighbourhood
        self.min_nr_points_per_segment = min_nr_points_per_segment
        self.with_previously_computed_segments = with_previously_computed_segments

    def angle_difference_check(self, normal1, normal2):

        """

        :param normal1:
        :param normal2:
        :return:
        """

        # normal1, normal2 have to be unit vectors ( and that is the case as a result of the SVD process )

        # return np.arccos(np.clip(np.dot(normal1, normal2), -1.0, 1.0)) * 180./np.pi <= self.angle_diff_threshold
        return angle_difference_compute(normal1, normal2) <= self.angle_diff_threshold

    def disntance_3D_set_check(
        self, point, segment_id, X, X_Y_Z_Columns, Segment_ID_Column
    ):

        """

        :param point:
        :param segment_id:
        :param X:
        :param X_Y_Z_Columns:
        :param Segment_ID_Column:
        :return:
        """

        point_mask = X[:, Segment_ID_Column] == segment_id

        # x,y,z
        # np.linalg.norm(X[point_mask, :3] - point.reshape(1, 3), ord=2, axis=1)
        # np.linalg.norm(X[point_mask, :3] - point.reshape(1, 3), ord=2, axis=1)
        # can be optimized by changing the norm
        return (
            np.min(
                np.linalg.norm(X[point_mask, :3] - point.reshape(1, 3), ord=2, axis=1)
            )
            <= self.disntance_3D_threshold
        )

    def compute_distance_orthogonal(self, candidate_point, plane_point, plane_normal):

        d = -plane_point.dot(plane_normal)
        distance = (plane_normal.dot(candidate_point) + d) / np.linalg.norm(
            plane_normal
        )

        return distance

    def distance_orthogonal_check(self, candidate_point, plane_point, plane_normal):

        """

        :param candidate_point:
        :param plane_point:
        :param plane_normal:
        :return:
        """

        # d = -plane_point.dot(plane_normal)
        # distance = (plane_normal.dot(candidate_point) + d) / np.linalg.norm(plane_normal)

        distance = self.compute_distance_orthogonal(
            candidate_point, plane_point, plane_normal
        )
        return distance - self.distance_orthogonal_threshold <= 0

    def lowest_local_suface_variance_check(self, llsv):
        """

        :param llsv:
        :return:
        """

        return llsv <= self.llsv_threshold

    def _fit(self, X, y=None):
        """

        :param X:
        :param y:
        :return:
        """

        # the 'Segment_ID_Column' was already added!
        if X.shape[1] == 18:
            self.with_previously_computed_segments = True

        return self
        pass

    def _transform(self, X):
        """

        :param X:
        :return:
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2
        X_Y_Z_Columns = [X_Column, Y_Column, Z_Column]

        EpochID_Column = 3
        # Lowest local surface variation
        # llsv_Column = -2  # the column ID

        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Normal_Columns = [
            Eigenvector2x_Column,
            Eigenvector2y_Column,
            Eigenvector2z_Column,
        ]

        # default, the points are part of NO segment ( e.g. -1 )
        Default_No_Segment = -1
        # default standard deviation for points that are not "core points"
        Default_std_deviation_of_no_core_point = -1

        # the new column is added only if it wasn't already added in previously
        if not self.with_previously_computed_segments:

            new_columns = np.full((X.shape[0], 1), Default_No_Segment, dtype=float)
            X = np.hstack((X, new_columns))

            new_columns_std_deviation = np.full(
                (X.shape[0], 1), Default_std_deviation_of_no_core_point, dtype=float
            )
            X = np.hstack((X, new_columns_std_deviation))

        Segment_ID_Column = 17
        Standard_deviation_Column = 18

        mask_epoch0 = X[:, EpochID_Column] == 0
        mask_epoch1 = X[:, EpochID_Column] == 1

        epoch0_set = X[mask_epoch0, :3]  # x,y,z
        epoch1_set = X[mask_epoch1, :3]  # x,y,z

        _epoch = [Epoch(epoch0_set), Epoch(epoch1_set)]

        _epoch[0].build_kdtree()
        _epoch[1].build_kdtree()

        # sort by "Lowest local surface variation"
        Sort_indx_epoch0 = X[mask_epoch0, llsv_Column].argsort()
        Sort_indx_epoch1 = X[mask_epoch1, llsv_Column].argsort()
        Sort_indx_epoch = [Sort_indx_epoch0, Sort_indx_epoch1]

        offset_in_X = [0, Sort_indx_epoch0.shape[0]]

        # initialization required between multiple iterations of these transform
        seg_id = np.max(X[:, Segment_ID_Column])

        for epoch_id in range(2):
            # seg_id = -1
            for indx_row in Sort_indx_epoch[epoch_id] + offset_in_X[epoch_id]:
                if X[indx_row, Segment_ID_Column] < 0:  # not part of a segment yet
                    seg_id += 1
                    X[indx_row, Segment_ID_Column] = seg_id

                    cumulative_distance_for_std_deviation = 0
                    nr_points_for_std_deviation = 0

                    # this step can be preprocessed in a vectorized way!
                    indx_kd_tree_list = _epoch[epoch_id].kdtree.radius_search(
                        X[indx_row, X_Y_Z_Columns], self.radius
                    )[: self.max_nr_points_neighbourhood]
                    for indx_kd_tree in indx_kd_tree_list:
                        if (
                            X[indx_kd_tree + offset_in_X[epoch_id], Segment_ID_Column]
                            < 0
                            and self.angle_difference_check(
                                X[indx_row, Normal_Columns],
                                X[indx_kd_tree + offset_in_X[epoch_id], Normal_Columns],
                            )
                            and self.disntance_3D_set_check(
                                X[indx_kd_tree + offset_in_X[epoch_id], X_Y_Z_Columns],
                                seg_id,
                                X,
                                X_Y_Z_Columns,
                                Segment_ID_Column,
                            )
                            and self.distance_orthogonal_check(
                                X[indx_kd_tree + offset_in_X[epoch_id], X_Y_Z_Columns],
                                X[indx_row, X_Y_Z_Columns],
                                X[indx_row, Normal_Columns],
                            )
                            and self.lowest_local_suface_variance_check(
                                X[indx_kd_tree + offset_in_X[epoch_id], llsv_Column]
                            )
                        ):
                            X[
                                indx_kd_tree + offset_in_X[epoch_id], Segment_ID_Column
                            ] = seg_id
                            cumulative_distance_for_std_deviation += (
                                self.compute_distance_orthogonal(
                                    X[
                                        indx_kd_tree + offset_in_X[epoch_id],
                                        X_Y_Z_Columns,
                                    ],
                                    X[indx_row, X_Y_Z_Columns],
                                    X[indx_row, Normal_Columns],
                                )
                                ** 2
                            )
                            nr_points_for_std_deviation += 1
                    # floating equality test must be changed with a more robust test !!!
                    # cast to int for a better testing !!!
                    nr_points_segment = np.count_nonzero(
                        X[:, Segment_ID_Column] == seg_id
                    )
                    # not enough points
                    if nr_points_segment < self.min_nr_points_per_segment:
                        mask_seg_id = X[:, Segment_ID_Column] == seg_id
                        X[mask_seg_id, Segment_ID_Column] = Default_No_Segment
                        seg_id -= 1  # since we don't have a new segment
                    else:
                        X[indx_row, Standard_deviation_Column] = (
                            cumulative_distance_for_std_deviation
                            / nr_points_for_std_deviation
                        )
        return X


class PostSegmentation(BaseTransformer):
    def __init__(self, skip=False, compute_normal=True):
        super().__init__(skip=skip)
        self.compute_normal = compute_normal

    def compute_distance_orthogonal(self, candidate_point, plane_point, plane_normal):

        d = -plane_point.dot(plane_normal.T)
        distance = (plane_normal.dot(candidate_point) + d) / np.linalg.norm(
            plane_normal
        )

        return distance

    def pca_compute_normal_and_mean(self, X):

        """

        :param x:
        :param X:
        :return:
        """

        size = X.shape[0]

        X_avg = np.mean(X, axis=0)  # compute mean
        B = X - np.tile(X_avg, (size, 1))

        # Find principal components (SVD)
        U, S, VT = np.linalg.svd(B.T / np.sqrt(size), full_matrices=0)

        assert S[0] != 0
        assert S[1] != 0
        assert S[2] != 0

        # Eig. values,
        # Eig. Vector0, Eig. Vector1, Eig. Vector2(Normal),
        # initial guess for normal position
        return (
            S.reshape(1, -1),
            U[:, 0].reshape(1, -1),
            U[:, 1].reshape(1, -1),
            U[:, 2].reshape(1, -1),
            X_avg.reshape(1, -1),
        )

    def _fit(self, X, y=None):

        """
        :param X:
        :param y:
        :return:
        """

        return self
        pass

    def _transform(self, X):

        """

        :param X:
        :return:
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2
        X_Y_Z_Columns = [X_Column, Y_Column, Z_Column]

        EpochID_Column = 3
        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Segment_ID_Column = 17

        Standard_deviation_Column = 18

        Eigval = [
            Eigenvalue0_Column,
            Eigenvalue1_Column,
            Eigenvalue2_Column,
        ]

        Eigvec0 = [Eigenvector0x_Column, Eigenvector0y_Column, Eigenvector0z_Column]

        Eigvec1 = [
            Eigenvector1x_Column,
            Eigenvector1y_Column,
            Eigenvector1z_Column,
        ]

        Normal_Columns = [
            Eigenvector2x_Column,
            Eigenvector2y_Column,
            Eigenvector2z_Column,
        ]

        # default, the points are part of NO segment ( e.g. -1 )
        Default_No_Segment = -1
        # default standard deviation for points that are not "core points"
        Default_std_deviation_of_no_core_point = -1

        max = int(X[:, Segment_ID_Column].max())

        for i in range(0, max + 1):

            mask = X[:, Segment_ID_Column] == float(i)
            set_cloud = X[
                mask, :3
            ]  # extract all points, that are part of the same segment
            eig_values, e0, e1, normal, position = self.pca_compute_normal_and_mean(
                set_cloud
            )

            indexes = np.where(mask == True)[0]

            # compute the closest point from the current segment to calculated "position"
            indx_min_in_indexes = np.linalg.norm(
                x=set_cloud - position, axis=1
            ).argmin()
            indx_min_in_X = indexes[indx_min_in_indexes]

            X[indx_min_in_X, Eigval] = eig_values
            X[indx_min_in_X, Eigvec0] = e0
            X[indx_min_in_X, Eigvec1] = e1

            if self.compute_normal:
                X[indx_min_in_X, Normal_Columns] = normal

            cumulative_distance_for_std_deviation = 0
            nr_points_for_std_deviation = indexes.shape[0] - 1
            for indx in indexes:
                cumulative_distance_for_std_deviation += (
                    self.compute_distance_orthogonal(
                        X[indx, X_Y_Z_Columns],
                        X[indx_min_in_X, X_Y_Z_Columns],
                        normal.reshape(1, -1),
                    )
                    ** 2
                )

            X[indx_min_in_X, Standard_deviation_Column] = (
                cumulative_distance_for_std_deviation / nr_points_for_std_deviation
            )

        return X


class ExtractSegments(BaseTransformer):
    def __init__(self, skip=False):
        """

        :param skip:
        """

        super(ExtractSegments, self).__init__(skip=skip)

    def _fit(self, X, y=None):
        """

        :param X:
        :param y:
        :return:
        """

        return self
        pass

    def _transform(self, X):

        """

        :param X:
        :return: A vector of segments.
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2

        EpochID_Column = 3
        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Segment_ID_Column = 17

        Standard_deviation_Column = 18

        # new column
        Nr_points_seg_Column = 19  # 18

        nr_columns_segment = 20  # 19

        max = int(X[:, Segment_ID_Column].max())
        X_Segments = np.empty((int(max) + 1, nr_columns_segment), dtype=float)

        for i in range(0, max + 1):

            mask = X[:, Segment_ID_Column] == float(i)
            set_cloud = X[mask, :]  # all
            nr_points = set_cloud.shape[0]

            # arg_min = set_cloud[:, llsv_Column].argmin()
            # X_Segments[i, :-1] = set_cloud[arg_min, :]

            mask_std = set_cloud[:, Standard_deviation_Column] != float(-1)
            set_cloud_std = set_cloud[mask_std, :]
            assert (
                set_cloud_std.shape[0] == 1
            ), "Only one element of the segment has standard deviation computed!"
            X_Segments[i, :-1] = set_cloud_std[0, :]

            X_Segments[i, -1] = nr_points

        return X_Segments

    pass


# class ExtendedClassifier(RandomForestClassifier):
#
#     def __init__(
#             self,
#             angle_diff_threshold=1,
#             neighborhood_search_radius=3,
#             threshold_probability_most_similar=0.8,
#             diff_between_most_similar_2=0.1
#     ):
#         """
#
#         :param angle_diff_threshold:
#         :param neighborhood_search_radius:
#         :param threshold_probability_most_similar:
#         :param diff_between_most_similar_2:
#         """
#
#         super().__init__()
#
#         self.angle_diff_threshold = angle_diff_threshold
#         self.neighborhood_search_radius = neighborhood_search_radius
#         self.threshold_probability_most_similar = threshold_probability_most_similar
#         self.diff_between_most_similar_2 = diff_between_most_similar_2
#
#     def compute_similarity_between(self, seg_epoch0, seg_epoch1):
#
#         """
#
#         :param seg_epoch0:
#         :param seg_epoch1:
#         :return:
#         """
#
#         X_Column = 0
#         Y_Column = 1
#         Z_Column = 2
#
#         EpochID_Column = 3
#         Eigenvalue0_Column = 4
#         Eigenvalue1_Column = 5
#         Eigenvalue2_Column = 6
#         Eigenvector0x_Column = 7
#         Eigenvector0y_Column = 8
#         Eigenvector0z_Column = 9
#         Eigenvector1x_Column = 10
#         Eigenvector1y_Column = 11
#         Eigenvector1z_Column = 12
#         Eigenvector2x_Column = 13
#         Eigenvector2y_Column = 14
#         Eigenvector2z_Column = 15
#         llsv_Column = 16
#         Segment_ID_Column = 17
#
#         Nr_points_seg_Column = 18
#
#         Normal_Columns = [Eigenvector2x_Column, Eigenvector2y_Column, Eigenvector2z_Column]
#
#         # angle = np.arccos(
#         #     np.clip(np.dot(seg_epoch0[Normal_Columns], seg_epoch1[Normal_Columns]), -1.0, 1.0)
#         # ) * 180./np.pi
#         angle = angle_difference_compute(seg_epoch0[Normal_Columns], seg_epoch1[Normal_Columns])
#
#         points_density_seg_epoch0 = \
#             seg_epoch0[Nr_points_seg_Column] / (seg_epoch0[Eigenvalue0_Column] * seg_epoch0[Eigenvalue1_Column])
#
#         points_density_seg_epoch1 = \
#             seg_epoch1[Nr_points_seg_Column] / (seg_epoch1[Eigenvalue0_Column] * seg_epoch1[Eigenvalue1_Column])
#
#         points_density_diff = abs(points_density_seg_epoch0 - points_density_seg_epoch1)
#
#         eigen_value_smallest_diff = abs(seg_epoch0[Eigenvalue2_Column] - seg_epoch1[Eigenvalue2_Column])
#         eigen_value_largest_diff = abs(seg_epoch0[Eigenvalue0_Column] - seg_epoch1[Eigenvalue0_Column])
#         eigen_value_middle_diff = abs(seg_epoch0[Eigenvalue1_Column] - seg_epoch1[Eigenvalue1_Column])
#
#         nr_points_diff = abs(seg_epoch0[Nr_points_seg_Column] - seg_epoch1[Nr_points_seg_Column])
#
#         return np.array([
#             angle,
#             points_density_diff,
#             eigen_value_smallest_diff, eigen_value_largest_diff, eigen_value_middle_diff,
#             nr_points_diff
#         ])
#
#     def build_X_similarity(self, y_row, X):
#
#         """
#
#         :param y_row:
#         :param X:
#         :return:
#         """
#
#         X_Column = 0
#         Y_Column = 1
#         Z_Column = 2
#
#         EpochID_Column = 3
#         Eigenvalue0_Column = 4
#         Eigenvalue1_Column = 5
#         Eigenvalue2_Column = 6
#         Eigenvector0x_Column = 7
#         Eigenvector0y_Column = 8
#         Eigenvector0z_Column = 9
#         Eigenvector1x_Column = 10
#         Eigenvector1y_Column = 11
#         Eigenvector1z_Column = 12
#         Eigenvector2x_Column = 13
#         Eigenvector2y_Column = 14
#         Eigenvector2z_Column = 15
#         llsv_Column = 16
#         Segment_ID_Column = 17
#
#         Nr_points_seg_Column = 18
#
#         Normal_Columns = [Eigenvector2x_Column, Eigenvector2y_Column, Eigenvector2z_Column]
#
#         seg_epoch0 = X[int(y_row[0]), :]
#         seg_epoch1 = X[int(y_row[1]), :]
#
#         return self.compute_similarity_between(seg_epoch0, seg_epoch1)
#
#     def fit(self, X, y):
#
#         """
#
#         :param X:
#         :param y:
#         :return:
#         """
#
#         X_similarity = np.apply_along_axis(
#             lambda y_row: self.build_X_similarity(y_row, X),
#             1,
#             y
#         )
#
#         # extra functionality
#         print("Classifier Fit")
#         return super().fit(X_similarity, y[:, 2])
#
#     # def predict(self, X):
#     #     # extra functionality
#     #
#     #     X_similarity = np.apply_along_axis(
#     #         lambda y_row: self.build_X_similarity(y_row, X),
#     #         1,
#     #         y
#     #     )
#     #
#     #     print("Classifier Predict")
#     #     return super().predict(X_similarity)
#
#     def predict(self, X):
#
#         """
#
#         :param X:
#         :return:
#         """
#
#         X_Column = 0
#         Y_Column = 1
#         Z_Column = 2
#
#         Segment_ID_Column = 17
#         EpochID_Column = 3
#
#         mask_epoch0 = X[:, EpochID_Column] == 0
#         mask_epoch1 = X[:, EpochID_Column] == 1
#
#         epoch0_set = X[mask_epoch0, :]  # all
#         epoch1_set = X[mask_epoch1, :]  # all
#
#         self.epoch1_segments = Epoch(epoch1_set[:, [X_Column, Y_Column, Z_Column]])
#         self.epoch1_segments.build_kdtree()
#
#         list_segments_pair = np.empty((0, epoch0_set.shape[1] + epoch1_set.shape[1]))
#
#         # this operation can be parallelized
#         for epoch0_set_row in epoch0_set:
#
#             list_candidates = self.epoch1_segments.kdtree.radius_search(
#                 epoch0_set_row, self.neighborhood_search_radius)
#
#             list_classified = np.array([
#                 super(RandomForestClassifier, self).predict_proba(
#                     self.compute_similarity_between(
#                         epoch0_set_row,
#                         epoch1_set[candidate, :]
#                     ).reshape(1, -1)
#                 )[0][1]
#                 for candidate in list_candidates
#             ])
#
#             if len(list_classified) < 2:
#                 continue
#
#             most_similar = list_classified.argsort()[-2:]
#
#             if(most_similar[1] >= self.threshold_probability_most_similar and
#                     abs(most_similar[1]-most_similar[0]) >= self.diff_between_most_similar_2):
#
#                 list_segments_pair = np.vstack(
#                     (
#                         list_segments_pair,
#                         np.hstack(
#                             (epoch0_set_row, epoch1_set[most_similar[-1], :])
#                         ).reshape(1, -1)
#                     )
#                 )
#
#         return list_segments_pair


class BuildSimilarityFeature_and_y(ABC):
    def __init__(self):

        super().__init__()

    @abstractmethod
    def generate_extended_y(self, X):
        """

        :param X:
        :return:
        """
        pass

    def compute(self, X, y=None):
        """

        :param X:
        :return:
        """

        y_extended = self.generate_extended_y(X)

        X_similarity = np.apply_along_axis(
            lambda y_row: self._build_X_similarity(y_row, X), 1, y_extended
        )

        return (X_similarity, y_extended[:, 2])

    def _build_X_similarity(self, y_row, X):
        """

        :param y_row:
            ( segment epoch0 id, segment epoch1 id, label(0/1) )
        :param X:
            numpy containing a segment on each row
        :return:
            numpy array containing the similarity value between 2 segments
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2

        EpochID_Column = 3
        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Segment_ID_Column = 17

        Standard_deviation_Column = 18
        Nr_points_seg_Column = 19  # 18

        Normal_Columns = [
            Eigenvector2x_Column,
            Eigenvector2y_Column,
            Eigenvector2z_Column,
        ]

        seg_epoch0 = X[int(y_row[0]), :]
        seg_epoch1 = X[int(y_row[1]), :]

        return compute_similarity_between(seg_epoch0, seg_epoch1)


class BuildTuplesOfSimilarityFeature_and_y(BuildSimilarityFeature_and_y):
    def __init__(self):

        super(BuildTuplesOfSimilarityFeature_and_y, self).__init__()

    def generate_extended_y(self, X):

        return X
        pass

    def compute(self, X, y):

        """

        :param X:
            numpy array of segments.
        :param y:
            numpy array where each row is of the following form ( segment ID epoch0, segment ID epoch1, label(0/1) )
        :return:
            touple of
                similarity feature (as a function of segment ID epoch0, segment ID epoch1) -> numpy array
                label (0/1) -> numpy array (n,)
        """

        assert y.shape[1] == 3, "rows of y must be of size 3!"

        y_extended = y

        X_similarity = np.apply_along_axis(
            lambda y_row: self._build_X_similarity(y_row, X), 1, y_extended
        )

        return (X_similarity, y_extended[:, 2])


class BuildSimilarityFeature_and_y_RandomPairs(BuildSimilarityFeature_and_y):
    def __init__(self):

        super(BuildSimilarityFeature_and_y_RandomPairs, self).__init__()

    def generate_extended_y(self, X):

        """

        :param X:
        :return:
        """

        Segment_ID_Column = 17
        EpochID_Column = 3

        mask_epoch0 = X[:, EpochID_Column] == 0
        mask_epoch1 = X[:, EpochID_Column] == 1

        epoch0_set = X[mask_epoch0, :]  # all
        epoch1_set = X[mask_epoch1, :]  # all

        nr_pairs = min(epoch0_set.shape[0], epoch1_set.shape[0]) // 3

        indx0_seg_id = random.sample(range(epoch0_set.shape[0]), nr_pairs)
        indx1_seg_id = random.sample(range(epoch1_set.shape[0]), nr_pairs)

        set0_seg_id = epoch0_set[indx0_seg_id, Segment_ID_Column]
        set1_seg_id = epoch1_set[indx1_seg_id, Segment_ID_Column]

        rand_y_01 = list(np.random.randint(0, 2, nr_pairs))

        return np.array([set0_seg_id, set1_seg_id, rand_y_01]).T


class BuildSimilarityFeature_and_y_Visually(BuildSimilarityFeature_and_y):
    def __init__(self):

        super(BuildSimilarityFeature_and_y_Visually, self).__init__()

        self.current_pair = [None] * 2
        self.constructed_extended_y = np.empty(shape=(0, 3))

    # def controller(self, evt):
    #     """
    #
    #     :param evt:
    #     :return:
    #     """
    #
    #     if not evt.actor:
    #         return  # no hit, return
    #     print("point coords =", evt.picked3d)
    #     if evt.isPoints:
    #         print(evt.actor)
    #         self.current_pair[int(evt.actor.epoch)] = evt.actor.id
    #
    #     if self.current_pair[0] != None and self.current_pair[1] != None:
    #
    #         # we have a pair
    #         self.add_pair_button.status(self.add_pair_button.states[1])
    #     else:
    #         # we don't
    #         self.add_pair_button.status(self.add_pair_button.states[0])
    #
    #
    #     # print("full event dump:", evt)

    def toggle_transparenct(self, evt):

        if evt.keyPressed == "z":
            # print("transparency toggle")
            for segment in self.sets:
                if segment.alpha() < 1.0:
                    segment.alpha(1)
                else:
                    segment.alpha(0.5)
            self.plt.render()

        if evt.keyPressed == "g":
            # print("toggle red")
            for segment in self.sets:
                if segment.epoch == 0:
                    if segment.isOn == True:
                        segment.off()
                    else:
                        segment.on()
                    segment.isOn = not segment.isOn
            self.plt.render()

        if evt.keyPressed == "d":
            # print("toggle green")
            for segment in self.sets:
                if segment.epoch == 1:
                    if segment.isOn == True:
                        segment.off()
                    else:
                        segment.on()
                    segment.isOn = not segment.isOn
            self.plt.render()

    def controller(self, evt):

        """

        :param evt:
        :return:
        """
        if not evt.actor:
            # no hit, return
            return
        logger = logging.getLogger("py4dgeo")
        logger.debug("point coords =%s", str(evt.picked3d), exc_info=1)
        # print("point coords =", evt.picked3d)
        if evt.isPoints:
            logger.debug("evt.actor = s", str(evt.actor))
            # print(evt.actor)
            self.current_pair[int(evt.actor.epoch)] = evt.actor.id

        if self.current_pair[0] != None and self.current_pair[1] != None:

            # we have a pair
            self.add_pair_button.status(self.add_pair_button.states[1])
        else:
            # we don't
            self.add_pair_button.status(self.add_pair_button.states[0])

        # print("full event dump:", evt)

    def event_add_pair_button(self):
        """

        :return:
        """

        if self.current_pair[0] != None and self.current_pair[1] != None:

            try:
                self.constructed_extended_y = np.vstack(
                    (
                        self.constructed_extended_y,
                        np.array(
                            [
                                self.current_pair[0],
                                self.current_pair[1],
                                int(self.label.status()),
                            ]
                        ),
                    )
                )

                self.current_pair[0] = None
                self.current_pair[1] = None
                self.label.status(self.label.states[0])  # firs state "None"

                self.add_pair_button.switch()
            except:
                # print("You must select 0 or 1 as label!!!")
                logger = logging.getLogger("py4dgeo")
                logger.error("You must select 0 or 1 as label")

    def segments_visualizer(self, X):
        """

        :param X:
        :return:
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2
        EpochID_Column = 3

        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15

        Segment_ID_Column = 17

        self.sets = []

        max = X.shape[0]
        # colors = getDistinctColors(max)
        colors = [(1, 0, 0), (0, 1, 0)]
        self.plt = Plotter(axes=3)

        self.plt.add_callback("EndInteraction", self.controller)
        self.plt.add_callback("KeyPress", self.toggle_transparenct)

        for i in range(0, max):

            # mask = X[:, 17] == float(i)
            # set_cloud = X[mask, :3]  # x,y,z

            if X[i, EpochID_Column] == 0:
                color = colors[0]
            else:
                color = colors[1]

            # self.sets = self.sets + [Points(set_cloud, colors[i], alpha=1, r=10)]

            # self.sets = self.sets + [ Point( pos=(X[i, 0],X[i, 1],X[i, 2]), r=15, c=colors[i], alpha=1 ) ]
            ellipsoid = Ellipsoid(
                pos=(X[i, 0], X[i, 1], X[i, 2]),
                axis1=(
                    X[i, Eigenvector0x_Column] * X[i, Eigenvalue0_Column] * 0.5,
                    X[i, Eigenvector0y_Column] * X[i, Eigenvalue0_Column] * 0.5,
                    X[i, Eigenvector0z_Column] * X[i, Eigenvalue0_Column] * 0.3,
                ),
                axis2=(
                    X[i, Eigenvector1x_Column] * X[i, Eigenvalue1_Column] * 0.5,
                    X[i, Eigenvector1y_Column] * X[i, Eigenvalue1_Column] * 0.5,
                    X[i, Eigenvector1z_Column] * X[i, Eigenvalue1_Column] * 0.5,
                ),
                axis3=(
                    X[i, Eigenvector2x_Column] * 0.1,
                    X[i, Eigenvector2y_Column] * 0.1,
                    X[i, Eigenvector2z_Column] * 0.1,
                ),
                res=24,
                c=color,
                alpha=1,
            )
            # ellipsoid.caption(txt=str(i), size=(0.1,0.05))
            ellipsoid.id = X[i, Segment_ID_Column]
            ellipsoid.epoch = X[i, EpochID_Column]
            ellipsoid.isOn = True
            self.sets = self.sets + [ellipsoid]

        self.label = self.plt.add_button(
            # self.label.switch(),
            # self.switch_label(),
            lambda: self.label.switch(),
            states=["Label (0/1)", "0", "1"],  # None
            c=["w", "w", "w"],
            bc=["bb", "lr", "lg"],
            pos=(0.90, 0.25),
            size=24,
        )

        self.add_pair_button = self.plt.add_button(
            self.event_add_pair_button,
            states=["Select pair", "Add pair"],
            c=["w", "w"],
            bc=["lg", "lr"],
            pos=(0.90, 0.15),
            size=24,
        )

        self.plt.show(
            self.sets,
            Text2D(
                "Select multiple pairs of red-green Ellipsoids with their corresponding labels (0/1) and then press 'Select pair'\n"
                "'z' - toggle transparency on/off 'g' - toggle on/off red ellipsoids 'd' toggle on/off red ellipsoids",
                pos="top-left",
                bg="k",
                s=0.7,
            ),
        ).close()
        return self.constructed_extended_y

    def generate_extended_y(self, X):

        """

        :param X:
        :return:
        """

        return self.segments_visualizer(X)

        pass


class ClassifierWrapper(ClassifierMixin, BaseEstimator):
    """An example classifier which implements a 1-NN algorithm.

    For more information regarding how to build your own classifier, read more
    in the :ref:`User Guide <user_guide>`.

    Parameters
    ----------
    demo_param : str, default='demo'
        A parameter used for demonstation of how to pass and store paramters.

    Attributes
    ----------
    X_ : ndarray, shape (n_samples, n_features)
        The input passed during :meth:`fit`.
    y_ : ndarray, shape (n_samples,)
        The labels passed during :meth:`fit`.
    classes_ : ndarray, shape (n_classes,)
        The classes seen at :meth:`fit`.
    """

    def __init__(
        self,
        angle_diff_threshold=1,
        neighborhood_search_radius=3,
        threshold_probability_most_similar=0.8,
        diff_between_most_similar_2=0.1,
        classifier=RandomForestClassifier(),
    ):

        """

        :param angle_diff_threshold:
        :param neighborhood_search_radius:
            Spatial proximity of corresponding planes is considered by using a neighbourhood
            limited to 3 m for correspondencesearch.
        :param threshold_probability_most_similar:
            Lower bound threshold probability for the most similar plane.
        :param diff_between_most_similar_2:
            Lower bound threshold of difference between first 2, most similar planes.
        :param classifier:
            The classifier used, default is RandomForestClassifier.
        """

        super().__init__()

        self.angle_diff_threshold = angle_diff_threshold
        self.neighborhood_search_radius = neighborhood_search_radius
        self.threshold_probability_most_similar = threshold_probability_most_similar
        self.diff_between_most_similar_2 = diff_between_most_similar_2
        self.classifier = classifier

    def fit(self, X, y):
        """A reference implementation of a fitting function for a classifier.

        Parameters
        ----------
        X : array-like, shape (n_samples, n_features)
            The training input samples.
        y : array-like, shape (n_samples,)
            The target values. An array of int.

        Returns
        -------
        self : object
            Returns self.
        """
        # Check that X and y have correct shape
        X, y = check_X_y(X, y)
        # Store the classes seen during fit
        self.classes_ = unique_labels(y)

        self.X_ = X
        self.y_ = y
        # Return the classifier
        # return self
        return self.classifier.fit(X, y)

    def predict(self, X):
        """A reference implementation of a prediction for a classifier.

        Parameters
        ----------
        X : array-like, shape (n_samples, n_features)
            The input samples.

        Returns
        -------
        y : ndarray, shape (n_samples,)
            The label for each sample is the label of the closest sample
            seen during fit.
        """
        # Check is fit had been called
        check_is_fitted(self, ["X_", "y_"])

        # Input validation
        X = check_array(X)

        # closest = np.argmin(euclidean_distances(X, self.X_), axis=1)
        # return self.y_[closest]

        X_Column = 0
        Y_Column = 1
        Z_Column = 2

        Segment_ID_Column = 17
        EpochID_Column = 3

        # if self.cross_validation_is_active == True:
        #     # the input 'X', in this scenario, is represented by the 'similarity feature'
        #     # and it is used during cross-validation learning
        #     return super(RandomForestClassifier, self).predict(X)

        mask_epoch0 = X[:, EpochID_Column] == 0
        mask_epoch1 = X[:, EpochID_Column] == 1

        epoch0_set = X[mask_epoch0, :]  # all
        epoch1_set = X[mask_epoch1, :]  # all

        self.epoch1_segments = Epoch(epoch1_set[:, [X_Column, Y_Column, Z_Column]])
        self.epoch1_segments.build_kdtree()

        list_segments_pair = np.empty((0, epoch0_set.shape[1] + epoch1_set.shape[1]))

        # this operation can be parallelized
        for epoch0_set_row in epoch0_set:

            list_candidates = self.epoch1_segments.kdtree.radius_search(
                epoch0_set_row, self.neighborhood_search_radius
            )

            list_classified = np.array(
                [
                    # super(RandomForestClassifier, self)
                    # self.predict_proba(
                    self.classifier.predict_proba(
                        compute_similarity_between(
                            epoch0_set_row, epoch1_set[candidate, :]
                        ).reshape(1, -1)
                    )[0][1]
                    for candidate in list_candidates
                ]
            )

            if len(list_classified) < 2:
                continue

            most_similar = list_classified.argsort()[-2:]

            if (
                most_similar[1] >= self.threshold_probability_most_similar
                and abs(most_similar[1] - most_similar[0])
                >= self.diff_between_most_similar_2
            ):

                list_segments_pair = np.vstack(
                    (
                        list_segments_pair,
                        np.hstack(
                            (epoch0_set_row, epoch1_set[most_similar[-1], :])
                        ).reshape(1, -1),
                    )
                )

        return list_segments_pair


class SimplifiedClassifier(RandomForestClassifier):
    def __init__(
        self,
        angle_diff_threshold=1,
        neighborhood_search_radius=3,
        threshold_probability_most_similar=0.8,
        diff_between_most_similar_2=0.1,
        # cross_validation_is_active=False,
    ):
        """

        :param angle_diff_threshold:
        :param neighborhood_search_radius:
        :param threshold_probability_most_similar:
        :param diff_between_most_similar_2:
        """

        super().__init__()

        self.angle_diff_threshold = angle_diff_threshold
        self.neighborhood_search_radius = neighborhood_search_radius
        self.threshold_probability_most_similar = threshold_probability_most_similar
        self.diff_between_most_similar_2 = diff_between_most_similar_2

    # def compute_similarity_between(self, seg_epoch0, seg_epoch1):
    #
    #     """
    #
    #     :param seg_epoch0:
    #     :param seg_epoch1:
    #     :return:
    #     """
    #
    #     X_Column = 0
    #     Y_Column = 1
    #     Z_Column = 2
    #
    #     EpochID_Column = 3
    #     Eigenvalue0_Column = 4
    #     Eigenvalue1_Column = 5
    #     Eigenvalue2_Column = 6
    #     Eigenvector0x_Column = 7
    #     Eigenvector0y_Column = 8
    #     Eigenvector0z_Column = 9
    #     Eigenvector1x_Column = 10
    #     Eigenvector1y_Column = 11
    #     Eigenvector1z_Column = 12
    #     Eigenvector2x_Column = 13
    #     Eigenvector2y_Column = 14
    #     Eigenvector2z_Column = 15
    #     llsv_Column = 16
    #     Segment_ID_Column = 17
    #
    #     Nr_points_seg_Column = 18
    #
    #     Normal_Columns = [Eigenvector2x_Column, Eigenvector2y_Column, Eigenvector2z_Column]
    #
    #     # angle = np.arccos(
    #     #     np.clip(np.dot(seg_epoch0[Normal_Columns], seg_epoch1[Normal_Columns]), -1.0, 1.0)
    #     # ) * 180./np.pi
    #     angle = angle_difference_compute(seg_epoch0[Normal_Columns], seg_epoch1[Normal_Columns])
    #
    #     points_density_seg_epoch0 = \
    #         seg_epoch0[Nr_points_seg_Column] / (seg_epoch0[Eigenvalue0_Column] * seg_epoch0[Eigenvalue1_Column])
    #
    #     points_density_seg_epoch1 = \
    #         seg_epoch1[Nr_points_seg_Column] / (seg_epoch1[Eigenvalue0_Column] * seg_epoch1[Eigenvalue1_Column])
    #
    #     points_density_diff = abs(points_density_seg_epoch0 - points_density_seg_epoch1)
    #
    #     eigen_value_smallest_diff = abs(seg_epoch0[Eigenvalue2_Column] - seg_epoch1[Eigenvalue2_Column])
    #     eigen_value_largest_diff = abs(seg_epoch0[Eigenvalue0_Column] - seg_epoch1[Eigenvalue0_Column])
    #     eigen_value_middle_diff = abs(seg_epoch0[Eigenvalue1_Column] - seg_epoch1[Eigenvalue1_Column])
    #
    #     nr_points_diff = abs(seg_epoch0[Nr_points_seg_Column] - seg_epoch1[Nr_points_seg_Column])
    #
    #     return np.array([
    #         angle,
    #         points_density_diff,
    #         eigen_value_smallest_diff, eigen_value_largest_diff, eigen_value_middle_diff,
    #         nr_points_diff
    #     ])

    def fit(self, X, y):
        """

        :param X:
        :param y:
        :return:
        """

        print("Classifier Fit")
        return super().fit(X, y)

    def predict(self, X):
        """

        :param X:
        :return:
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2

        Segment_ID_Column = 17
        EpochID_Column = 3

        mask_epoch0 = X[:, EpochID_Column] == 0
        mask_epoch1 = X[:, EpochID_Column] == 1

        epoch0_set = X[mask_epoch0, :]  # all
        epoch1_set = X[mask_epoch1, :]  # all

        self.epoch1_segments = Epoch(epoch1_set[:, [X_Column, Y_Column, Z_Column]])
        self.epoch1_segments.build_kdtree()

        list_segments_pair = np.empty((0, epoch0_set.shape[1] + epoch1_set.shape[1]))

        # this operation can be parallelized
        for epoch0_set_row in epoch0_set:

            list_candidates = self.epoch1_segments.kdtree.radius_search(
                epoch0_set_row, self.neighborhood_search_radius
            )

            list_classified = np.array(
                [
                    # super(RandomForestClassifier, self)
                    self.predict_proba(
                        compute_similarity_between(
                            epoch0_set_row, epoch1_set[candidate, :]
                        ).reshape(1, -1)
                    )[0][1]
                    for candidate in list_candidates
                ]
            )

            if len(list_classified) < 2:
                continue

            most_similar = list_classified.argsort()[-2:]

            if (
                most_similar[1] >= self.threshold_probability_most_similar
                and abs(most_similar[1] - most_similar[0])
                >= self.diff_between_most_similar_2
            ):

                list_segments_pair = np.vstack(
                    (
                        list_segments_pair,
                        np.hstack(
                            (epoch0_set_row, epoch1_set[most_similar[-1], :])
                        ).reshape(1, -1),
                    )
                )

        return list_segments_pair


class PB_M3C2:
    def __init__(
        self,
        add_LLSV_and_PCA=AddLLSVandPCA(),
        segmentation=Segmentation(),
        second_segmentation=Segmentation(with_previously_computed_segments=True),
        extract_segments=ExtractSegments(),
        classifier=ClassifierWrapper(),
    ):

        """
        :param add_LLSV_and_PCA:
            lowest local surface variation and PCA computattion. (computes the normal vector as well)
        :param segmentation:
            The object used for the first segmentation.
        :param second_segmentation:
            The object used for the second segmentation.
        :param extract_segments:
            The object used for building the segments.
        :param classifier:
            An instance of ClassifierWrapper class. The default wrapped classifier used is sk-learn RandomForest.
        """

        if second_segmentation:
            assert (
                second_segmentation.with_previously_computed_segments == True
            ), "Second segmentation must have: with_previously_computed_segments=True"

        self._add_LLSV_and_PCA = add_LLSV_and_PCA
        self._segmentation = segmentation
        self._second_segmentation = second_segmentation
        self._extract_segments = extract_segments
        self._classifier = classifier

    def _reconstruct_input_with_normals(self, epoch, epoch_id):

        """
        It is an adapter from [x, y, z, N_x, N_y, N_z, Segment_ID] column structure of input 'epoch'
        to an output equivalent with the following pipeline computation:
                ("Transform LLSVandPCA"), ("Transform Segmentation"), ("Transform Second Segmentation")

        Note: When comparing distance results between this notebook and the base algorithm notebook, you might notice,
        that results do not necessarily agree even if the given segmentation information is exactly
        the same as the one computed in the base algorithm.
        This is due to the reconstruction process in this algorithm being forced to select the segment position
        (exported as the core point) from the segment points instead of reconstructing the correct position
        from the base algorithm.

        :param epoch:
            Epoch object where each row has the following format: [x, y, z, N_x, N_y, N_z, Segment_ID]
        :param epoch_id:
            is 0 or 1 and represents one of the epochs used as part of distance computation.
        :return:
                [
                    x,y,z, -> Center of the Mass
                    EpochID_Column, ->0/1
                    Eigenvalue 1, Eigenvalue 2, Eigenvalue 3,
                    Eigenvector0 (x,y,z),
                    Eigenvector1 (x,y,z),
                    Eigenvector2 (x,y,z), -> Normal vector
                    llsv_Column, -> lowest local surface variation
                    Segment_ID_Column,
                    Standard_deviation_Column
                ]
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2

        EpochID_Column = 3
        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Segment_ID_Column = 17

        Standard_deviation_Column = 18

        # default standard deviation for points that are not "core points"
        Default_std_deviation_of_no_core_point = -1

        # x, y, z, N_x, N_y, N_z, Segment_ID
        assert epoch.shape[1] == 3 + 3 + 1, "epoch size mismatch!"

        return np.hstack(
            (
                epoch[:, :3],  # x,y,z      X 3
                np.full(
                    (epoch.shape[0], 1), epoch_id, dtype=float
                ),  # EpochID_Column    X 1
                np.full((epoch.shape[0], 3), 0, dtype=float),  # Eigenvalue X 3
                np.full(
                    (epoch.shape[0], 6), 0, dtype=float
                ),  # Eigenvector0, Eigenvector1        X 6
                epoch[:, 3:6],  # Eigenvector2      X 3
                np.full((epoch.shape[0], 1), 0, dtype=float).reshape(
                    -1, 1
                ),  # llsv_Column
                epoch[:, -1].reshape(-1, 1),  # Segment_ID_Column
                np.full(
                    (epoch.shape[0], 1),
                    Default_std_deviation_of_no_core_point,
                    dtype=float,
                ).reshape(
                    -1, 1
                ),  # Standard_deviation_Column
            )
        )

    def _reconstruct_input_without_normals(self, epoch, epoch_id):

        """
        It is an adapter from [x, y, z, Segment_ID] column structure of input 'epoch'
        to an output equivalent with the following pipeline computation:
            ("Transform LLSVandPCA"), ("Transform Segmentation"), ("Transform Second Segmentation")

        Note: When comparing distance results between this notebook and the base algorithm notebook, you might notice,
        that results do not necessarily agree even if the given segmentation information is exactly
        the same as the one computed in the base algorithm.
        This is due to the reconstruction process in this algorithm being forced to select the segment position
        (exported as the core point) from the segment points instead of reconstructing the correct position
        from the base algorithm.

        :param epoch:
            Epoch object where each row contains by: [x, y, z, Segment_ID]
        :param epoch_id:
            is 0 or 1 and represents one of the epochs used as part of distance computation.
        :return:
                [
                    x,y,z, -> Center of the Mass
                    EpochID_Column, ->0/1
                    Eigenvalue 1, Eigenvalue 2, Eigenvalue 3,
                    Eigenvector0 (x,y,z),
                    Eigenvector1 (x,y,z),
                    Eigenvector2 (x,y,z), -> Normal vector
                    llsv_Column, -> lowest local surface variation
                    Segment_ID_Column,
                    Standard_deviation_Column
                ]
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2

        EpochID_Column = 3
        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Segment_ID_Column = 17

        Standard_deviation_Column = 18

        # default standard deviation for points that are not "core points"
        Default_std_deviation_of_no_core_point = -1

        # [x, y, z, Segment_ID] or [x, y, z, N_x, N_y, N_z, Segment_ID]
        assert (
            epoch.shape[1] == 3 + 1 or epoch.shape[1] == 3 + 3 + 1
        ), "epoch size mismatch!"

        return np.hstack(
            (
                epoch[:, :3],  # x,y,z     X 3
                np.full(
                    (epoch.shape[0], 1), epoch_id, dtype=float
                ),  # EpochID_Column X 1
                np.full((epoch.shape[0], 3), 0, dtype=float),  # Eigenvalue X 3
                np.full(
                    (epoch.shape[0], 6), 0, dtype=float
                ),  # Eigenvector0, Eigenvector1 X 6
                np.full((epoch.shape[0], 3), 0, dtype=float),  # Eigenvector2 X 3
                np.full((epoch.shape[0], 1), 0, dtype=float).reshape(
                    -1, 1
                ),  # llsv_Column
                epoch[:, -1].reshape(-1, 1),  # Segment_ID_Column
                np.full(
                    (epoch.shape[0], 1),
                    Default_std_deviation_of_no_core_point,
                    dtype=float,
                ).reshape(
                    -1, 1
                ),  # Standard_deviation_Column
            )
        )

    def build_labelled_similarity_features_interactively(
        self,
        epoch0,
        epoch1,
        build_similarity_feature_and_y=BuildSimilarityFeature_and_y_Visually(),
    ):

        """
        Given 2 Epochs, it builds a pair of features and labels used for learning.

        :param epoch0:
            Epoch object.
        :param epoch1:
            Epoch object.
        :param build_similarity_feature_and_y:
            The object used for extracting the features applied as part of similarity algorithm.
        :return:
            pairs of 'similarity features', labels
        """

        if not interactive_available:
            logger = logging.getLogger("py4dgeo")
            logger.error("Interactive session not available in this environment.")
            return

        X0 = np.hstack((epoch0.cloud[:, :], np.zeros((epoch0.cloud.shape[0], 1))))
        X1 = np.hstack((epoch1.cloud[:, :], np.ones((epoch1.cloud.shape[0], 1))))

        X = np.vstack((X0, X1))

        labeling_pipeline = Pipeline(
            [
                ("Transform AddLLSVandPCA", self._add_LLSV_and_PCA),
                ("Transform Segmentation", self._segmentation),
                ("Transform Second Segmentation", self._second_segmentation),
                ("Transform ExtractSegments", self._extract_segments),
            ]
        )

        labeling_pipeline.fit(X)

        return build_similarity_feature_and_y.compute(labeling_pipeline.transform(X))

    def export_segments_for_labelling(
        self,
        epoch0,
        epoch1,
        x_y_z_id_epoch0_file_name="x_y_z_id_epoch0.xyz",
        x_y_z_id_epoch1_file_name="x_y_z_id_epoch1.xyz",
        extracted_segments_file_name="extracted_segments.seg",
    ):

        """
        For each epoch, it returns the segmentation of the point cloud as a numpy array (n,4)
        and it also serializes them using the provided file names.
        where each row has the following structure: x, y, z, segment_id

        It also generates a numpy array of segments of the form:
                    X_Column, Y_Column, Z_Column, -> Center of Gravity
                    EpochID_Column, -> 0/1
                    Eigenvalue0_Column, Eigenvalue1_Column, Eigenvalue2_Column,
                    Eigenvector0x_Column, Eigenvector0y_Column, Eigenvector0z_Column,
                    Eigenvector1x_Column, Eigenvector1y_Column, Eigenvector1z_Column,
                    Eigenvector2x_Column, Eigenvector2y_Column, Eigenvector2z_Column, -> Normal vector
                    llsv_Column, -> lowest local surface variation
                    Segment_ID_Column,
                    Standard_deviation_Column,
                    Nr_points_seg_Column,

        :param epoch0:
            Epoch object
        :param epoch1:
            Epoch object
        :return:
            x_y_z_id_epoch0
            x_y_z_id_epoch1
            extracted_segments
        """

        X0 = np.hstack((epoch0.cloud[:, :], np.zeros((epoch0.cloud.shape[0], 1))))
        X1 = np.hstack((epoch1.cloud[:, :], np.ones((epoch1.cloud.shape[0], 1))))

        X = np.vstack((X0, X1))

        pipe_segmentation = Pipeline(
            [
                ("Transform AddLLSVandPCA", self._add_LLSV_and_PCA),
                ("Transform Segmentation", self._segmentation),
                ("Transform Second Segmentation", self._second_segmentation),
            ]
        )

        pipe_segmentation.fit(X)
        # 'out' contains the segmentation of the point cloud.
        out = pipe_segmentation.transform(X)

        self._extract_segments.fit(out)
        # 'extracted_segments' contains the new set of segments
        extracted_segments = self._extract_segments.transform(out)

        X_Column = 0
        Y_Column = 1
        Z_Column = 2
        EpochID_Column = 3
        Segment_ID_Column = 17

        Extract_Columns = [X_Column, Y_Column, Z_Column, Segment_ID_Column]

        mask_epoch0 = out[:, EpochID_Column] == 0
        mask_epoch1 = out[:, EpochID_Column] == 1

        out_epoch0 = out[mask_epoch0, :]
        out_epoch1 = out[mask_epoch1, :]

        x_y_z_id_epoch0 = out_epoch0[:, Extract_Columns]  # x,y,z, Seg_ID
        x_y_z_id_epoch1 = out_epoch1[:, Extract_Columns]  # x,y,z, Seg_ID

        np.savetxt(x_y_z_id_epoch0_file_name, x_y_z_id_epoch0, delimiter=",")
        np.savetxt(x_y_z_id_epoch1_file_name, x_y_z_id_epoch1, delimiter=",")
        np.savetxt(extracted_segments_file_name, extracted_segments, delimiter=",")

        return x_y_z_id_epoch0, x_y_z_id_epoch1, extracted_segments

    def build_labelled_similarity_features(
        self,
        extracted_segments_file_name="extracted_segments.seg",
        tuples_seg_epoch0_seg_epoch1_label_file_name=None,
        tuple_feature_y=BuildTuplesOfSimilarityFeature_and_y(),
    ):

        """
        Build similarity features from pairs of segments and assign the corresponding labels.

        :param extracted_segments:
            same format as the one exported by export_segments_for_labelling()
            numpy array with shape (m, 20) where the column structure is as following:
                [
                    X_Column, Y_Column, Z_Column, -> Center of Gravity
                    EpochID_Column, -> 0/1
                    Eigenvalue0_Column, Eigenvalue1_Column, Eigenvalue2_Column,
                    Eigenvector0x_Column, Eigenvector0y_Column, Eigenvector0z_Column,
                    Eigenvector1x_Column, Eigenvector1y_Column, Eigenvector1z_Column,
                    Eigenvector2x_Column, Eigenvector2y_Column, Eigenvector2z_Column, -> Normal vector
                    llsv_Column, -> lowest local surface variation
                    Segment_ID_Column,
                    Standard_deviation_Column,
                    Nr_points_seg_Column,
                ]
        :param pair_segments_epoch0_epoch1_label:
            numpy array (m, 3)
        :return:
            pairs of 'similarity features', labels
        """

        # Resolve the given path
        filename = find_file(extracted_segments_file_name)

        logger = logging.getLogger("py4dgeo")

        # Read it
        try:
            logger.info(f"Reading segments from file '{filename}'")
            extracted_segments = np.genfromtxt(filename, delimiter=",")
        except ValueError:
            raise Py4DGeoError("Malformed file: " + str(filename))

        # Resolve the given path
        filename = find_file(tuples_seg_epoch0_seg_epoch1_label_file_name)

        # Read it
        try:
            logger.info(
                f"Reading tuples of (segment epoch0, segment epoch1, label) from file '{filename}'"
            )
            tuples_seg_epoch0_seg_epoch1_label = np.genfromtxt(filename, delimiter=",")
        except ValueError:
            raise Py4DGeoError("Malformed file: " + str(filename))

        return tuple_feature_y.compute(
            X=extracted_segments, y=tuples_seg_epoch0_seg_epoch1_label
        )

    def training(self, X, y):

        """
        It applies the training algorithm for the input pairs of features 'X' and labels 'y'.

        :param X:
            features. numpy array of shape (n, p)

            Where 'p' represents an arbitrary number of features
            generated by 'tuple_feature_y' as part of 'build_labelled_similarity_features' call.
        :param y:
            labels. numpy array of shape (n,)
        :return:
        """

        training_pipeline = Pipeline(
            [
                ("Classifier", self._classifier),
            ]
        )
        training_pipeline.fit(X, y)

    def predict(self, epoch0, epoch1):

        """
        After extracting the segments from epoch0 and epoch1, it predicts which one corresponds and which doesn't.

        :param epoch0:
            Epoch object.
        :param epoch1:
            Epoch object.
        :return: Return a numpy array (m,) of 0/1
        """

        X0 = np.hstack((epoch0.cloud[:, :], np.zeros((epoch0.cloud.shape[0], 1))))
        X1 = np.hstack((epoch1.cloud[:, :], np.ones((epoch1.cloud.shape[0], 1))))

        # | x | y | z | epoch I.D.
        X = np.vstack((X0, X1))

        predicting_pipeline = Pipeline(
            [
                ("Transform AddLLSVandPCA", self._add_LLSV_and_PCA),
                ("Transform Segmentation", self._segmentation),
                ("Transform Second Segmentation", self._second_segmentation),
                ("Transform ExtractSegments", self._extract_segments),
                ("Classifier", self._classifier),
            ]
        )

        return predicting_pipeline.predict(X)
        pass

    # predict_scenario4
    def predict_update(self, previous_segmented_epoch, epoch1):

        """
        "predict_scenario4"

        :param previous_segmented_epoch:
        :param epoch1:
        :return:
        """

        assert False, "Please, recheck this functionality first!"

        Segment_ID_Column = 17

        X0 = self._reconstruct_input_with_normals(
            epoch=previous_segmented_epoch, epoch_id=0
        )

        post_segmentation_transform = PostSegmentation(compute_normal=True)
        post_segmentation_transform.fit(X0)
        X0_post_seg = post_segmentation_transform.transform(X0)

        max_segment_id_X0 = int(X0_post_seg[:, Segment_ID_Column].max())

        # transform X1
        X1 = np.hstack((epoch1.cloud[:, :], np.ones((epoch1.cloud.shape[0], 1))))

        pipe = Pipeline(
            [
                ("Transform AddLLSVandPCA", self._add_LLSV_and_PCA),
                ("Transform Segmentation", self._segmentation),
                ("Transform Second Segmentation", self._second_segmentation),
            ]
        )

        self._add_LLSV_and_PCA.skip = False
        self._segmentation.skip = False
        self._second_segmentation.skip = False

        pipe.fit(X1)
        X1_post_pipe = pipe.transform(X1)

        for indx in range(0, X1_post_pipe.shape[0]):
            if X1_post_pipe[indx, Segment_ID_Column] != -1:
                X1_post_pipe[indx, Segment_ID_Column] += max_segment_id_X0

        X = np.vstack((X0, X1))

        predict_pipe = Pipeline(
            [
                ("Transform ExtractSegments", self._extract_segments),
                ("Classifier", self._classifier),
            ]
        )

        self._extract_segments.skip = False
        self._classifier.skip = False

        predict_pipe.fit(X)
        return predict_pipe.predict(X)

    def compute_distances(self, epoch0, epoch1, alignment_error=1.1):

        """
        Compute the distance between 2 epochs. It also adds the following properties at the end of the computation:
            distances, corepoints (corepoints of epoch0), epochs (epoch0, epoch1), uncertainties

        :param epoch0:
            Epoch object.
        :param epoch1:
            Epoch object.
        :param alignment_error:
            alignment error reg between point clouds.
        :return:
            distances, uncertainties
        """

        X_Column = 0
        Y_Column = 1
        Z_Column = 2

        EpochID_Column = 3
        Eigenvalue0_Column = 4
        Eigenvalue1_Column = 5
        Eigenvalue2_Column = 6
        Eigenvector0x_Column = 7
        Eigenvector0y_Column = 8
        Eigenvector0z_Column = 9
        Eigenvector1x_Column = 10
        Eigenvector1y_Column = 11
        Eigenvector1z_Column = 12
        Eigenvector2x_Column = 13
        Eigenvector2y_Column = 14
        Eigenvector2z_Column = 15
        llsv_Column = 16
        Segment_ID_Column = 17

        Standard_deviation_Column = 18
        Nr_points_seg_Column = 19  # 18

        # Each row contains a pair of segments.
        segments_pair = self.predict(epoch0=epoch0, epoch1=epoch1)

        size_segment = int(segments_pair.shape[1] / 2)
        nr_pairs = segments_pair.shape[0]

        epoch0_segments = segments_pair[:, :size_segment]
        epoch1_segments = segments_pair[:, size_segment:]

        # seg_id_epoch0, X_Column0, Y_Column0, Z_Column0, seg_id_epoch1, X_Column1, Y_Column1, Z_Column1, distance, uncertaintie
        output = np.empty((0, 10), dtype=float)

        for indx in range(nr_pairs):

            segment_epoch0 = epoch0_segments[indx]
            segment_epoch1 = epoch1_segments[indx]

            t0_CoG = segment_epoch0[[X_Column, Y_Column, Z_Column]]
            t1_CoG = segment_epoch1[[X_Column, Y_Column, Z_Column]]

            Normal_Columns = [
                Eigenvector2x_Column,
                Eigenvector2y_Column,
                Eigenvector2z_Column,
            ]
            normal_vector_t0 = segment_epoch0[Normal_Columns]

            M3C2_dist = normal_vector_t0.dot(t0_CoG - t1_CoG)

            std_dev_normalized_squared_t0 = segment_epoch0[Standard_deviation_Column]
            std_dev_normalized_squared_t1 = segment_epoch1[Standard_deviation_Column]

            LoDetection = 1.96 * (
                np.sqrt(std_dev_normalized_squared_t0 + std_dev_normalized_squared_t1)
                + alignment_error
            )

            # seg_id_epoch0, X_Column0, Y_Column0, Z_Column0, seg_id_epoch1, X_Column1, Y_Column1, Z_Column1, distance, uncertaintie
            args = (
                np.array([segment_epoch0[Segment_ID_Column]]),
                t0_CoG,
                np.array([segment_epoch1[Segment_ID_Column]]),
                t1_CoG,
                np.array([M3C2_dist]),
                np.array([LoDetection]),
            )
            row = np.concatenate(args)
            output = np.vstack((output, row))

        # We don't return this anymore. It corresponds to the output structure of the original implementation.
        # return output

        # distance vector
        self.distances = output[:, -2]

        # corepoints to epoch0 ('initial' one)
        self.corepoints = Epoch(output[:, [1, 2, 3]])

        # epochs
        self.epochs = (epoch0, epoch1)

        self.uncertainties = np.empty(
            (output.shape[0], 1),
            dtype=np.dtype(
                [
                    ("lodetection", "<f8"),
                    ("spread1", "<f8"),
                    ("num_samples1", "<i8"),
                    ("spread2", "<f8"),
                    ("num_samples2", "<i8"),
                ]
            ),
        )

        self.uncertainties["lodetection"] = output[:, -1].reshape(-1, 1)

        self.uncertainties["spread1"] = np.sqrt(
            np.multiply(
                epoch0_segments[:, Standard_deviation_Column],
                epoch0_segments[:, Nr_points_seg_Column],
            )
        ).reshape(-1, 1)
        self.uncertainties["spread2"] = np.sqrt(
            np.multiply(
                epoch1_segments[:, Standard_deviation_Column],
                epoch1_segments[:, Nr_points_seg_Column],
            )
        ).reshape(-1, 1)

        self.uncertainties["num_samples1"] = (
            epoch0_segments[:, Nr_points_seg_Column].astype(int).reshape(-1, 1)
        )
        self.uncertainties["num_samples2"] = (
            epoch1_segments[:, Nr_points_seg_Column].astype(int).reshape(-1, 1)
        )

        return (self.distances, self.uncertainties)


def _build_input_scenario2_with_normals(epoch0, epoch1):

    """
    :param epoch0: x,y,z point cloud
    :param epoch1: x,y,z point cloud
    :return:
        # x,y,z, N_x,N_y,N_z, Segment_ID
        new_epoch0, new_epoch1
    """

    X_Column = 0
    Y_Column = 1
    Z_Column = 2

    EpochID_Column = 3
    Eigenvalue0_Column = 4
    Eigenvalue1_Column = 5
    Eigenvalue2_Column = 6
    Eigenvector0x_Column = 7
    Eigenvector0y_Column = 8
    Eigenvector0z_Column = 9
    Eigenvector1x_Column = 10
    Eigenvector1y_Column = 11
    Eigenvector1z_Column = 12
    Eigenvector2x_Column = 13
    Eigenvector2y_Column = 14
    Eigenvector2z_Column = 15
    llsv_Column = 16
    Segment_ID_Column = 17

    Standard_deviation_Column = 18
    Nr_points_seg_Column = 19  # 18

    Normal_Columns = [
        Eigenvector2x_Column,
        Eigenvector2y_Column,
        Eigenvector2z_Column,
    ]

    x_y_z_Columns = [X_Column, Y_Column, Z_Column]

    X0 = np.hstack((Epoch0.cloud[:, :], np.zeros((epoch0.cloud.shape[0], 1))))
    X1 = np.hstack((Epoch1.cloud[:, :], np.ones((epoch1.cloud.shape[0], 1))))

    X = np.vstack((X0, X1))

    transform_pipeline = Pipeline(
        [
            ("Transform AddLLSVandPCA", AddLLSVandPCA()),
            ("Transform Segmentation", Segmentation()),
        ]
    )

    transform_pipeline.fit(X)
    out = transform_pipeline.transform(X)

    mask_epoch0 = out[:, EpochID_Column] == 0  # epoch0
    mask_epoch1 = out[:, EpochID_Column] == 1  # epoch1

    new_epoch0 = out[mask_epoch0, :]  # extract epoch0
    new_epoch1 = out[mask_epoch1, :]  # extract epoch1

    new_epoch0 = new_epoch0[:, x_y_z_Columns + Normal_Columns + [Segment_ID_Column]]
    new_epoch1 = new_epoch1[:, x_y_z_Columns + Normal_Columns + [Segment_ID_Column]]

    # x,y,z, N_x,N_y,N_z, Segment_ID
    return new_epoch0, new_epoch1
    pass


def _build_input_scenario2_without_normals(epoch0, epoch1):

    """
    :param epoch0: x,y,z point cloud
    :param epoch1: x,y,z point cloud
    :return:
        # x,y,z, Segment_ID
        new_epoch0, new_epoch1
    """

    X_Column = 0
    Y_Column = 1
    Z_Column = 2

    EpochID_Column = 3
    Eigenvalue0_Column = 4
    Eigenvalue1_Column = 5
    Eigenvalue2_Column = 6
    Eigenvector0x_Column = 7
    Eigenvector0y_Column = 8
    Eigenvector0z_Column = 9
    Eigenvector1x_Column = 10
    Eigenvector1y_Column = 11
    Eigenvector1z_Column = 12
    Eigenvector2x_Column = 13
    Eigenvector2y_Column = 14
    Eigenvector2z_Column = 15
    llsv_Column = 16
    Segment_ID_Column = 17

    Standard_deviation_Column = 18
    Nr_points_seg_Column = 19  # 18

    x_y_z_Columns = [X_Column, Y_Column, Z_Column]

    Normal_Columns = [
        Eigenvector2x_Column,
        Eigenvector2y_Column,
        Eigenvector2z_Column,
    ]

    X0 = np.hstack((epoch0.cloud[:, :], np.zeros((epoch0.cloud.shape[0], 1))))
    X1 = np.hstack((epoch1.cloud[:, :], np.ones((epoch1.cloud.shape[0], 1))))

    X = np.vstack((X0, X1))

    transform_pipeline = Pipeline(
        [
            ("Transform AddLLSVandPCA", AddLLSVandPCA()),
            ("Transform Segmentation", Segmentation()),
        ]
    )

    transform_pipeline.fit(X)
    out = transform_pipeline.transform(X)

    mask_epoch0 = out[:, EpochID_Column] == 0  # epoch0
    mask_epoch1 = out[:, EpochID_Column] == 1  # epoch1

    new_epoch0 = out[mask_epoch0, :]  # extract epoch0
    new_epoch1 = out[mask_epoch1, :]  # extract epoch1

    new_epoch0 = new_epoch0[:, x_y_z_Columns + [Segment_ID_Column]]
    new_epoch1 = new_epoch1[:, x_y_z_Columns + [Segment_ID_Column]]

    # x,y,z, Segment_ID
    return new_epoch0, new_epoch1
    pass


class PB_M3C2_with_segments(PB_M3C2):
    def __init__(
        self,
        post_segmentation=PostSegmentation(compute_normal=True),
        classifier=ClassifierWrapper(),
    ):
        """

        :param post_segmentation:

        :param classifier:
            An instance of ClassifierWrapper class. The default wrapped classifier used is sk-learn RandomForest.
        """

        super().__init__(
            add_LLSV_and_PCA=None,
            segmentation=None,
            second_segmentation=None,
            extract_segments=ExtractSegments(),
            classifier=classifier,
        )
        self._post_segmentation = post_segmentation

    # def build_labelled_similarity_features_interactively(
    #     self,
    #     epoch0,
    #     epoch1,
    #     build_similarity_feature_and_y=BuildSimilarityFeature_and_y_Visually(),
    # ):
    #
    #     """
    #     Given 2 Epochs, it builds a pair of features and labels used for learning.
    #     :param epoch0:
    #     :param epoch1:
    #     :return:
    #         parir of (features, labels)
    #     """
    #
    #     if self._post_segmentation.compute_normal:
    #         X0 = self._reconstruct_input_without_normals(epoch=epoch0, epoch_id=0)
    #         X1 = self._reconstruct_input_without_normals(epoch=epoch1, epoch_id=1)
    #     else:
    #         X0 = self._reconstruct_input_with_normals(epoch=epoch0, epoch_id=0)
    #         X1 = self._reconstruct_input_with_normals(epoch=epoch1, epoch_id=1)
    #
    #     X = np.vstack((X0, X1))
    #
    #     labeling_pipeline = Pipeline(
    #         [
    #             ("Transform Post Segmentation", self._post_segmentation),
    #             ("Transform ExtractSegments", self._extract_segments),
    #         ]
    #     )
    #
    #     labeling_pipeline.fit(X)
    #
    #     return build_similarity_feature_and_y.compute(labeling_pipeline.transform(X))

    def build_labelled_similarity_features_interactively(
        self,
        epoch0,
        epoch1,
        build_similarity_feature_and_y=BuildSimilarityFeature_and_y_Visually(),
    ):

        assert (
            "segment_id" in epoch0.additional_dimensions.dtype.names
        ), "the epoch doesn't contain 'segment_id' as an additional dimension"

        epoch0 = np.concatenate(
            (epoch0.cloud, epoch0.additional_dimensions["segment_id"]), axis=1
        )

        assert (
            "segment_id" in epoch1.additional_dimensions.dtype.names
        ), "the epoch doesn't contain 'segment_id' as an additional dimension"

        epoch1 = np.concatenate(
            (epoch1.cloud, epoch1.additional_dimensions["segment_id"]), axis=1
        )

        if self._post_segmentation.compute_normal:
            X0 = self._reconstruct_input_without_normals(epoch=epoch0, epoch_id=0)
            X1 = self._reconstruct_input_without_normals(epoch=epoch1, epoch_id=1)
        else:
            X0 = self._reconstruct_input_with_normals(epoch=epoch0, epoch_id=0)
            X1 = self._reconstruct_input_with_normals(epoch=epoch1, epoch_id=1)

        X = np.vstack((X0, X1))

        transform_pipeline = Pipeline(
            [
                ("Transform Post Segmentation", self._post_segmentation),
                ("Transform ExtractSegments", self._extract_segments),
            ]
        )

        transform_pipeline.fit(X)
        return build_similarity_feature_and_y.compute(transform_pipeline.transform(X))

    def reconstruct_post_segmentation_output(
        self,
        epoch0,
        epoch1,
        extracted_segments_file_name="extracted_segments.seg",
    ):

        assert (
            "segment_id" in epoch0.additional_dimensions.dtype.names
        ), "the epoch doesn't contain 'segment_id' as an additional dimension"

        epoch0 = np.concatenate(
            (epoch0.cloud, epoch0.additional_dimensions["segment_id"]), axis=1
        )

        assert (
            "segment_id" in epoch1.additional_dimensions.dtype.names
        ), "the epoch doesn't contain 'segment_id' as an additional dimension"

        epoch1 = np.concatenate(
            (epoch1.cloud, epoch1.additional_dimensions["segment_id"]), axis=1
        )

        if self._post_segmentation.compute_normal:
            X0 = self._reconstruct_input_without_normals(epoch=epoch0, epoch_id=0)
            X1 = self._reconstruct_input_without_normals(epoch=epoch1, epoch_id=1)
        else:
            X0 = self._reconstruct_input_with_normals(epoch=epoch0, epoch_id=0)
            X1 = self._reconstruct_input_with_normals(epoch=epoch1, epoch_id=1)

        X = np.vstack((X0, X1))

        transform_pipeline = Pipeline(
            [
                ("Transform Post Segmentation", self._post_segmentation),
                ("Transform ExtractSegments", self._extract_segments),
            ]
        )

        transform_pipeline.fit(X)
        extracted_segments = transform_pipeline.transform(X)

        np.savetxt(extracted_segments_file_name, extracted_segments, delimiter=",")

        return epoch0, epoch1, extracted_segments

    def training(self, X, y):

        """
        It applies the training algorithm for the input pairs of features 'X' and labels 'y'.
        :param X: features.
        :param y: labels.
        :return:
        """

        training_predicting_pipeline = Pipeline(
            [
                # ("Transform Post Segmentation", self._post_segmentation),
                # ("Transform ExtractSegments", self._extract_segments),
                ("Classifier", self._classifier),
            ]
        )

        training_predicting_pipeline.fit(X, y)

        pass

    def predict(self, epoch0, epoch1):

        """
        For a set of pairs of segments, between Epoch and Epoch 1, it predicts which one corresponds and which don't.
        :param epoch0:
        :param epoch1:
        :return: Return a vector of 0/1
        """

        assert (
            "segment_id" in epoch0.additional_dimensions.dtype.names
        ), "the epoch doesn't contain 'segment_id' as an additional dimension"

        epoch0 = np.concatenate(
            (epoch0.cloud, epoch0.additional_dimensions["segment_id"]), axis=1
        )

        assert (
            "segment_id" in epoch1.additional_dimensions.dtype.names
        ), "the epoch doesn't contain 'segment_id' as an additional dimension"

        epoch1 = np.concatenate(
            (epoch1.cloud, epoch1.additional_dimensions["segment_id"]), axis=1
        )

        if self._post_segmentation.compute_normal:
            X0 = self._reconstruct_input_without_normals(epoch=epoch0, epoch_id=0)
            X1 = self._reconstruct_input_without_normals(epoch=epoch1, epoch_id=1)
        else:
            X0 = self._reconstruct_input_with_normals(epoch=epoch0, epoch_id=0)
            X1 = self._reconstruct_input_with_normals(epoch=epoch1, epoch_id=1)

        X = np.vstack((X0, X1))

        predicting_pipeline = Pipeline(
            [
                ("Transform Post Segmentation", self._post_segmentation),
                ("Transform ExtractSegments", self._extract_segments),
                ("Classifier", self._classifier),
            ]
        )

        return predicting_pipeline.predict(X)
        pass

    # the algorithm should be the same!
    # def compute_distances(self, epoch0, epoch1, alignment_error=1.1):


if __name__ == "__main__":

    util.ensure_test_data_availability()

    random.seed(10)
    np.random.seed(10)

    epoch0, epoch1 = read_from_xyz("plane_horizontal_t1.xyz", "plane_horizontal_t2.xyz")

    # *********************

    # ***************
    # Scenario 1

    # random.seed(10)
    # np.random.seed(10)
    #
    # Alg = PB_M3C2()
    #
    # # X, y = Alg.build_labelled_similarity_features_interactively(
    # #     epoch0=epoch0, epoch1=epoch1
    # # )
    # # Alg.training(X, y)
    #
    # (
    #     x_y_z_id_epoch0,
    #     x_y_z_id_epoch1,
    #     extracted_segments,
    # ) = Alg.export_segments_for_labelling(epoch0=epoch0, epoch1=epoch1)
    # extended_y = generate_random_y(
    #     extracted_segments, extended_y_file_name="locally_generated_extended_y.csv"
    # )
    # features, labels = Alg.build_labelled_similarity_features(
    #     extracted_segments_file_name="extracted_segments.seg",
    #     tuples_seg_epoch0_seg_epoch1_label_file_name="locally_generated_extended_y.csv",
    # )
    # Alg.training(features, labels)
    #
    # print(Alg.predict(epoch0=epoch0, epoch1=epoch1))
    # print(Alg.compute_distances(epoch0=epoch0, epoch1=epoch1))

    # random.seed(10)
    # np.random.seed(10)
    #
    # Alg2 = PB_M3C2(
    #     classifier=SimplifiedClassifier()
    #     # add_LLSV_and_PCA = AddLLSVandPCA(),
    #     # segmentation = Segmentation(),
    #     # second_segmentation = Segmentation(
    #     #     radius=5,
    #     #     angle_diff_threshold=10,
    #     #     disntance_3D_threshold=10,
    #     #     # distance_orthogonal_threshold=10, llsv_threshold=10, roughness_threshold=10,
    #     #     with_previously_computed_segments=True),
    #     # extract_segments = Extract_segments(),
    #     # build_similarity_feature_and_y = BuildSimilarityFeature_and_y_RandomPairs(),
    #     # classifier=ClassifierWrapper()
    # )
    #
    # X1, y1 = Alg2.build_labels(epoch0=epoch0, epoch1=epoch1)
    # Alg2.training(X, y)
    # print(Alg2.predict(epoch0=epoch0, epoch1=epoch1))
    # print(Alg2.distance(epoch0=epoch0, epoch1=epoch1))

    # *********************
    # scenario 2

    random.seed(10)
    np.random.seed(10)

    new_epoch0, new_epoch1 = _build_input_scenario2_without_normals(
        epoch0=epoch0, epoch1=epoch1
    )
    # new_epoch0, new_epoch1 = _build_input_scenario2_with_normals(epoch0=epoch0, epoch1=epoch1)

    alg_scenario2 = PB_M3C2_scenario2()
    X, y = alg_scenario2.build_labels(epoch0=new_epoch0, epoch1=new_epoch1)
    alg_scenario2.training(X, y)
    print(alg_scenario2.predict(epoch0=new_epoch0, epoch1=new_epoch1))
    print(alg_scenario2.distance(epoch0=new_epoch0, epoch1=new_epoch1))
