import os
import sys
import argparse
from loguru import logger
from glob import glob
from train.core.tester import Tester
#from train.core.tester_smpl import Tester
os.environ['PYOPENGL_PLATFORM'] = 'egl'
sys.path.append('')


def main(args):

    input_image_folder = args.image_folder
    output_path = args.output_folder
    os.makedirs(output_path, exist_ok=True)

    logger.add(
        os.path.join(output_path, 'demo.log'),
        level='INFO',
        colorize=False,
    )
    logger.info(f'Demo options: \n {args}')

    # ----- image_folder / mount sanity check -----
    if not os.path.isdir(input_image_folder):
        logger.error(f"image_folder is not a directory: {input_image_folder}")
        raise FileNotFoundError(f"image_folder is not a directory: {input_image_folder}")
    all_names = os.listdir(input_image_folder)
    IMG_EXT = ('.png', '.jpg', '.jpeg')
    image_names = [n for n in all_names if n.lower().endswith(IMG_EXT)]
    logger.info(f"image_folder={input_image_folder} | listdir count={len(all_names)} | images (.png/.jpg/.jpeg) count={len(image_names)}")
    if all_names:
        logger.info(f"First 5 listdir entries: {all_names[:5]}")
    if not image_names:
        # MPT only accepts .png/.jpg/.jpeg; if inputs are e.g. .webp, use a workdir with .jpg symlinks
        EXTRA_EXT = ('.webp', '.bmp', '.tiff', '.tif')
        extra = [n for n in all_names if n.lower().endswith(EXTRA_EXT)]
        if extra:
            import tempfile
            import shutil
            workdir = tempfile.mkdtemp(prefix="dpose_inputs_")
            try:
                for n in extra:
                    src = os.path.join(input_image_folder, n)
                    base = os.path.splitext(n)[0]
                    lnk = os.path.join(workdir, base + ".jpg")
                    os.symlink(src, lnk)
                input_image_folder = workdir
                image_names = [os.path.basename(os.path.splitext(n)[0] + ".jpg") for n in extra]
                logger.info(f"Using workdir {workdir} with {len(image_names)} symlinks (.jpg) for MPT")
            except Exception as e:
                logger.warning(f"Could not create symlink workdir: {e}. Proceeding with original folder.")
        else:
            logger.warning(
                f"No images with extension .png/.jpg/.jpeg in {input_image_folder}. "
                "Multi-person tracker and D-PoSE expect filenames ending with these. "
                f"All entries: {all_names[:20]}{'...' if len(all_names) > 20 else ''}"
            )

    tester = Tester(args)
    if args.eval_dataset == 'hbw':
        all_image_folder = glob(os.path.join(input_image_folder, 'images', args.data_split + '_small_resolution', '*', '*'))
        all_bbox_folder = glob(os.path.join('data/test_images/hbw_test_images_bbox', '*', '*','labels'))
        tester.load_yolov5_bboxes(all_bbox_folder)
        detections = None
        tester.run_on_hbw_folder(all_image_folder, detections, output_path, args.data_split, args.display)
    elif args.eval_dataset == 'ssp':
        dataframe_path = args.dataframe_path
        tester.run_on_dataframe(dataframe_path, output_path, args.display)
    else:
        all_image_folder = [input_image_folder]
        try:
            detections = tester.run_detector(all_image_folder)
        except Exception as e:
            logger.exception(f"run_detector failed: {e}")
            raise
        num_frames = [len(d) for d in detections] if detections else []
        logger.info(f"run_detector returned {len(detections)} folder(s), frame counts per folder: {num_frames}")
        if not detections or all(len(d) == 0 for d in detections):
            logger.error(
                "Detector returned 0 frames. Check: (1) image_folder has .png/.jpg/.jpeg files, "
                "(2) /workspace/shared/inputs is mounted (e.g. docker compose volume), "
                "(3) no exception was swallowed inside multi_person_tracker."
            )
        tester.run_on_image_folder(
            all_image_folder, detections, output_path, 
            visualize_proj=args.display, 
            export_only=True)

    del tester.model

    logger.info('================= END =================')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--cfg', type=str, default='configs/dpose_conf.yaml',
                        help='config file that defines model hyperparams')

    parser.add_argument('--ckpt', type=str, default='data/ckpt/paper_arxiv.ckpt',
                        help='checkpoint path')

    parser.add_argument('--image_folder', type=str, default='demo_images',
                        help='input image folder')

    parser.add_argument('--output_folder', type=str, default='demo_images/results',
                        help='output folder to write results')

    parser.add_argument('--tracker_batch_size', type=int, default=1,
                        help='batch size of object detector used for bbox tracking')
                        
    parser.add_argument('--display', action='store_true',
                        help='visualize the 3d body projection on image')

    parser.add_argument('--detector', type=str, default='yolo', choices=['yolo', 'maskrcnn'],
                        help='object detector to be used for bbox tracking')

    parser.add_argument('--yolo_img_size', type=int, default=416,
                        help='input image size for yolo detector')
    parser.add_argument('--eval_dataset', type=str, default=None)
    parser.add_argument('--dataframe_path', type=str, default='data/ssp_3d_test.npz')
    parser.add_argument('--data_split', type=str, default='test')

    args = parser.parse_args()
    main(args)
