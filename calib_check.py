import halcon as ha
import numpy as np
import matplotlib.pyplot as plt
import glob
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FC


def calibration(img_path_l, img_path_r=None):
    """
    根据路径进行双目/单目标定

    输入参数
    ----

    img_path_l, img_path_r: 相机标定文件路径, img_path_r为None时进行单目标定

    返回值
    ---
    calib_data_id, error: Halcon标定模型与误差
    """
    # 获取图片像素尺寸
    file_name_l = img_path_l + 'image_01'
    image = ha.read_image(file_name_l)
    width, height = ha.get_image_size(image)
    # scale = .1
    # 读取标定板与标定图像路径
    caltab_descr = 'XJcaltabNew_410_235mm.cpd'
    # caltab_thickness = 0.001
    num_cameras = 1
    num_calib_objects = 1
    img_l = glob.glob(pathname=img_path_l + '*.png')
    if img_path_r:
        img_r = glob.glob(pathname=img_path_r + '*.png')
        num_cameras = 2
    num_poses = len(img_l)
    # 初始化标定模型
    calib_data_id = ha.create_calib_data(
        'calibration_object', num_cameras, num_calib_objects)
    start_cam_par = (0.0125, 0.0, 0.0, 0.0, 0.0, 0.0, 3.45e-6,
                     3.45e-6, width[0]*.5, height[0]*.5, width[0], height[0])
    ha.set_calib_data_cam_param(
        calib_data_id, 'all', 'area_scan_polynomial', start_cam_par)
    ha.set_calib_data_calib_object(calib_data_id, 0, caltab_descr)
    # 标定过程
    num_ignored_img = 0
    for PoseIndex in range(num_poses):
        for CameraIndex in range(num_cameras):
            if CameraIndex == 0:
                file_name = img_l[PoseIndex]
            else:
                file_name = img_r[PoseIndex]
            image = ha.read_image(file_name)
            # 提取标志点
            try:
                ha.find_calib_object(image, calib_data_id,
                                     CameraIndex, 0, PoseIndex, [], [])
                ha.get_calib_data_observ_contours(
                    calib_data_id, 'caltab', CameraIndex, 0, PoseIndex)
                ha.get_calib_data_observ_contours(
                    calib_data_id, 'marks', CameraIndex, 0, PoseIndex)
                # ha.dev_display(Caltab)
            except ha.ffi.HOperatorError:
                num_ignored_img = num_ignored_img + 1
    try:
        error = ha.calibrate_cameras(calib_data_id)
        return calib_data_id, error
    except ha.ffi.HOperatorError:
        print('标定失败')


def calibration_pose(file_name, cam_par):
    """
    输入标定结果, 根据单张图片计算标定板位置

    输入参数
    ----

    file_name: 单张图片文件路径

    返回值
    ---
    pose: 单张图片标定板位置
    """
    # 获取图片像素尺寸
    image = ha.read_image(file_name)
    # width, height = ha.get_image_size(image)
    # scale = .1
    # 读取标定板与标定图像路径
    caltab_descr = 'XJcaltabNew_410_235mm.cpd'
    # caltab_thickness = 0.001
    num_cameras = 1
    num_calib_objects = 1
    # 初始化标定模型
    calib_data_id = ha.create_calib_data(
        'calibration_object', num_cameras, num_calib_objects)
    ha.set_calib_data_cam_param(
        calib_data_id, 'all', 'area_scan_polynomial', cam_par)
    # ha.set_calib_data_cam_param(calib_data_id, 'all', cam_par)
    ha.set_calib_data_calib_object(calib_data_id, 0, caltab_descr)
    # 标定过程
    try:
        ha.find_calib_object(image, calib_data_id, 0, 0, 0, [], [])
        ha.get_calib_data_observ_contours(calib_data_id, 'caltab', 0, 0, 0)
        ha.get_calib_data_observ_contours(calib_data_id, 'marks', 0, 0, 0)
        # ha.dev_display(Caltab)
    except ha.ffi.HOperatorError:
        return None
    try:
        ha.calibrate_cameras(calib_data_id)
        return calib_data_id
        # return ha.get_calib_data(calib_data_id, 'calib_obj_pose', [0, 0], 'init_pose')
    except ha.ffi.HOperatorError:
        return None


def wcs_to_img(pose, posex, pixel_x, pixel_y, line, param):
    """世界坐标系转换至图像坐标系"""
    cam0_hom_wcs = ha.pose_to_hom_mat3d(pose)
    cam0_hom_cam1 = ha.pose_to_hom_mat3d(posex)
    cam1_hom_cam0 = ha.hom_mat3d_invert(cam0_hom_cam1)
    cam1_hom_wcs = ha.hom_mat3d_compose(cam1_hom_cam0, cam0_hom_wcs)
    line_z = [0] * line
    x, y, z = ha.affine_trans_point_3d(cam1_hom_wcs, pixel_x, pixel_y, line_z)
    img_x, img_y = ha.project_3d_point(x, y, z, param)
    return img_x, img_y


def single_bias_data(calib_data_id, cam_par, pic):
    """
    计算每张图片内参重投影误差的偏差分布
    """
    # 获取用于比较的图片信息
    calib_single = calibration_pose(pic, cam_par)
    pose = ha.get_calib_data(
        calib_single, 'calib_obj_pose', [0, 0], 'init_pose')
    RCoord, CCoord, Index, pose0 = ha.get_calib_data_observ_points(
        calib_single, 0, 0, 0)
    # 计算重投影位置
    X = ha.get_calib_data(calib_data_id, 'calib_obj', 0, 'x')
    Y = ha.get_calib_data(calib_data_id, 'calib_obj', 0, 'y')
    cam_pose = ha.get_calib_data(calib_data_id, 'camera', 0, 'pose')
    RCoordX, CCoordX = wcs_to_img(pose, cam_pose, X, Y, len(X), cam_par)
    # 计算偏差
    deltaR = []
    deltaC = []
    diff = []
    for i in range(len(Index)):
        deltaR.append(RCoordX[Index[i]] - RCoord[i])
        deltaC.append(CCoordX[Index[i]] - CCoord[i])
        # if CCoordX[Index[i]] - CCoord[i] > 0.4:
        #     print(int(Index[i]))
        diff.append(
            np.sqrt((RCoordX[Index[i]] - RCoord[i])**2+(CCoordX[Index[i]] - CCoord[i])**2))
    # diff_total.append(np.mean(diff))
    diff_single = np.mean(diff)
    bias_list = np.array([RCoord, CCoord, deltaR, deltaC, diff])
    # bias_total = np.concatenate((bias_total, bias_list), axis=1)
    diff_single = np.sqrt(np.mean(deltaR)**2+np.mean(deltaC)**2)
    std_single = np.sqrt(np.std(deltaR, ddof=1)**2+np.std(deltaC, ddof=1)**2)
    return diff_single, std_single, bias_list


def multi_bias_data(calib_data_id, cam_par0, cam_par1, pic_l, pic_r):
    """
    计算每张图片双目重投影误差的偏差分布
    """
    # 读取检测图片信息
    calib_single = calibration_pose(pic_l, cam_par0)
    pose = ha.get_calib_data(
        calib_single, 'calib_obj_pose', [0, 0], 'init_pose')
    RCoord, CCoord, Index, pose0 = ha.get_calib_data_observ_points(
        calib_single, 0, 0, 0)
    calib_single = calibration_pose(pic_r, cam_par1)
    # poser = ha.get_calib_data(calib_single, 'calib_obj_pose', [0, 0], 'init_pose')
    RCoord1, CCoord1, Index1, pose0 = ha.get_calib_data_observ_points(
        calib_single, 0, 0, 0)
    # RCoord, CCoord, Index, pose0 = ha.get_calib_data_observ_points(calib_data_id, 0, 0, pic)
    # pose = ha.get_calib_data(calib_data_id, 'calib_obj_pose', [0, pic], 'pose')
    cam_pose = ha.get_calib_data(calib_data_id, 'camera', 1, 'pose')
    # RCoord1, CCoord1, Index1, pose1 = ha.get_calib_data_observ_points(calib_data_id, 1, 0, pic)

    cam0_hom_wcs = ha.pose_to_hom_mat3d(pose)
    cam0_hom_cam1 = ha.pose_to_hom_mat3d(cam_pose)
    cam1_hom_cam0 = ha.hom_mat3d_invert(cam0_hom_cam1)
    cam1_hom_wcs = ha.hom_mat3d_compose(cam1_hom_cam0, cam0_hom_wcs)

    world_x, world_y = ha.image_points_to_world_plane(
        cam_par0, pose, RCoord, CCoord, 'm')
    world_z = [0] * len(world_x)

    x, y, z = ha.affine_trans_point_3d(cam1_hom_wcs, world_x, world_y, world_z)
    RCoordX, CCoordX = ha.project_3d_point(x, y, z, cam_par1)
    # 计算偏差
    deltaR = np.array([])
    deltaC = np.array([])
    RCoord_co = np.array([])
    CCoord_co = np.array([])
    for i in range(len(Index)):
        try:
            Index1f = Index1.index(Index[i])
            if (Index1f >= 0):
                deltaR = np.append(deltaR, RCoordX[i] - RCoord1[Index1f])
                deltaC = np.append(deltaC, CCoordX[i] - CCoord1[Index1f])
                # if CCoordX[i] - CCoord1[Index1f] > 0.4:
                #     print(int(Index[i]))
                RCoord_co = np.append(RCoord_co, RCoord[i])
                CCoord_co = np.append(CCoord_co, CCoord[i])
        except Exception:
            continue
    # deltaR = np.array(RCoordX) - np.array(RCoord1)
    # deltaC = np.array(CCoordX) - np.array(CCoord1)
    diff = np.sqrt(deltaR*deltaR+deltaC*deltaC)
    bias_list = np.array([RCoord_co, CCoord_co, deltaR, deltaC, diff])
    # print(np.mean(deltaR),np.mean(deltaC),np.mean(diff))
    diff_single = np.sqrt(np.mean(deltaR)**2+np.mean(deltaC)**2)
    std_single = np.sqrt(np.std(deltaR, ddof=1)**2+np.std(deltaC, ddof=1)**2)
    return diff_single, std_single, bias_list


def plot_bias_simple(path_l, path_r, pathc_l, pathc_r, fig1, fig2):
    """
    简略绘图过程, 返回显示在textBrowser上的内容
    """
    calib_data_id, error = calibration(path_l, path_r)
    cam_par0 = ha.get_calib_data(calib_data_id, 'camera', 0, 'params')
    cam_par1 = ha.get_calib_data(calib_data_id, 'camera', 1, 'params')
    # num_cameras = ha.get_calib_data(calib_data_id, 'model', 'general', ['num_cameras'])[0]
    text_show = "<font size=\"4\">" + "标定误差: e="+str(round(error, 3)) + "</font><br/>"
    text_show += '<br/>每张图片重投影误差均值与标准差:<br/>'
    bias_total = np.array([[], [], [], [], []])
    ax1 = fig1.add_subplot(111)
    ax1.set_xticks([-0.6, -0.3, 0, 0.3, 0.6])
    ax1.set_yticks([-0.6, -0.3, 0, 0.3, 0.6])
    ax1.axis([-0.6, 0.6, -0.6, 0.6])
    ax1.grid()
    ax2 = fig2.add_subplot(111)
    ax2.axis([0, 4096, 0, 2160])
    plt.subplots_adjust(left=None, bottom=None, right=None,
                        top=None, wspace=0.3, hspace=0.3)
    diff_total = []
    for index in range(20):
        try:
            if pathc_l:
                img_list = glob.glob(pathname=pathc_l + '*.png')
                pic_l = img_list[index]
                pic_index = int(pic_l[-6:-4])
                if pathc_r:
                    pic_r = pathc_r + os.path.basename(img_list[index])
                    diff_single, std_single, bias_list = multi_bias_data(
                        calib_data_id, cam_par0, cam_par1, pic_l, pic_r)
                else:
                    diff_single, std_single, bias_list = single_bias_data(
                        calib_data_id, cam_par0, pic_l)
            elif pathc_r:
                img_list = glob.glob(pathname=pathc_r + '*.png')
                pic_r = img_list[index]
                pic_index = int(pic_r[-6:-4])
                diff_single, std_single, bias_list = single_bias_data(
                    calib_data_id, cam_par1, pic_r)
            diff_color = "black" if diff_single < 0.2 else "red" if diff_single > 0.4 else "blue"
            std_color = "black" if std_single < 0.2 else "red" if std_single > 0.4 else "blue"
            text_show += str(pic_index) + ': <font color=\"' + diff_color + '\">M=' + str(round(diff_single, 3)) + '</font> <font color=\"' + std_color + '\">s=' + str(round(std_single, 3)) + '</font><br/>'
            diff_total.append(diff_single)
            bias_total = np.concatenate((bias_total, bias_list), axis=1)
            ax1.scatter(bias_list[2], bias_list[3],  s=6)
            scale = [40*max(i-0.1, 0) for i in bias_list[4]]
            ax2.scatter(bias_list[1], bias_list[0], s=scale)
        except Exception:
            break  
    return text_show
    # ax1.set_xlabel("标志点行坐标")
    # ax1.set_ylabel("重投影误差")
    # ax2.set_xlabel("标志点列坐标")
    # ax2.set_ylabel("重投影误差")
