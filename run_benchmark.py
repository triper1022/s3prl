import os
import yaml
import glob
import torch
import random
import argparse
import importlib
import numpy as np
from shutil import copyfile
from argparse import Namespace
from ipdb import set_trace

from benchmark.runner import Runner


def get_benchmark_args():
    parser = argparse.ArgumentParser()

    # resume a training experiment or test a checkpoint
    # all args and config will be overwrited by the checkpoint except args.mode
    parser.add_argument('--past_exp')
    
    # start a new experiment
    parser.add_argument('--task', choices=['example', 'phone'])
    parser.add_argument('--mode', choices=['train', 'evaluate'])
    parser.add_argument('--config')

    # upstream settings
    parser.add_argument('--upstream', choices=['example', 'mfcc', 'mockingjay', 'apc'])
    parser.add_argument('--upstream_ckpt')
    parser.add_argument('--upstream_config')
    parser.add_argument('--upstream_trainable', action='store_true')

    # experiment directory, choose one to specify
    # expname uses the default root directory: result/benchmark
    parser.add_argument('--expdir')
    parser.add_argument('--expname')

    # options
    parser.add_argument('--seed', default=1337, type=int)
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--eval_init', action='store_true')

    args = parser.parse_args()

    if args.past_exp:
        # determine checkpoint path
        if os.path.isdir(args.past_exp):
            ckpt_pths = glob.glob(f'{args.past_exp}/states-*.ckpt')
            assert len(ckpt_pths) > 0
            ckpt_pths = sorted(ckpt_pths, key=lambda pth: int(pth.split('-')[-1].split('.')[0]))
            ckpt_pth = ckpt_pths[-1]
        else:
            ckpt_pth = args.past_exp
        
        # load checkpoint
        ckpt = torch.load(ckpt_pth, map_location='cpu')

        def update_args(old, new):
            old_dict = vars(old)
            new_dict = vars(new)
            old_dict.update(new_dict)
            return Namespace(**old_dict)

        # overwrite args and config
        mode = args.mode
        args = update_args(args, ckpt['Args'])
        config = ckpt['Config']
        args.mode = mode
        args.past_exp = ckpt_pth

    else:
        if args.expdir is None:
            args.expdir = f'result/benchmark/{args.expname}'
        os.makedirs(args.expdir, exist_ok=True)

        copyfile(args.config, f'{args.expdir}/{args.config.split("/")[-1]}')
        with open(args.config, 'r') as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

    return args, config


def main():
    # get config and arguments
    args, config = get_benchmark_args()

    # Fix seed and make backends deterministic
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True

    runner = Runner(args, config)
    eval(f'runner.{args.mode}')()
    runner.logger.close()


if __name__ == '__main__':
    main()