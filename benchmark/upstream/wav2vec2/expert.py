import os
import math
import yaml
import random

import torch
import torch.nn as nn
from torch.nn.utils.rnn import pad_sequence

from fairseq.models.wav2vec import Wav2Vec2Model

SAMPLE_RATE = 16000
EXAMPLE_SEC = 5


class UpstreamExpert(nn.Module):
    """
    The expert of Wav2vec 2.0
    """

    def __init__(self, ckpt_path, config_path, **kwargs):
        super(UpstreamExpert, self).__init__()

        cp = torch.load(ckpt_path)
        self.model = Wav2Vec2Model.build_model(cp['args'], task=None)
        self.model.load_state_dict(cp['model'])

        pseudo_input = torch.randn(1, SAMPLE_RATE * EXAMPLE_SEC)
        padding_mask = torch.zeros(1, SAMPLE_RATE * EXAMPLE_SEC).long().bool()
        pseudo_feature, padding_mask = self.model.extract_features(pseudo_input, padding_mask)

        self.output_dim = pseudo_feature.size(-1)

    # Interface
    def get_output_dim(self):
        return self.output_dim

    # Interface
    def forward(self, wavs):
        """
        Args:
            wavs:
                list of unpadded wavs [wav1, wav2, ...]
                each wav is in torch.FloatTensor with sample rate 16000
                and already put in the device assigned by command-line args

        Return:
            features:
                list of unpadded features [feat1, feat2, ...]
                each feat is in torch.FloatTensor and already
                put in the device assigned by command-line args
        """
        device = wavs[0].device
        wav_lengths = torch.LongTensor([len(wav) for wav in wavs]).to(device)
        wav_padding_mask = ~torch.lt(
            torch.arange(max(wav_lengths)).unsqueeze(0).to(device),
            wav_lengths.unsqueeze(1)
        )
        padded_wav = pad_sequence(wavs, batch_first=True)
        
        features, feat_padding_mask = self.model.extract_features(padded_wav, wav_padding_mask)
        feat_lengths = (features.size(1) - feat_padding_mask.sum(dim=-1)).tolist()

        features = [feat[:length] for feat, length in zip(features, feat_lengths)]
        return features