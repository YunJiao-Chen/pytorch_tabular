#!/usr/bin/env python
"""Tests for `pytorch_tabular` package."""
import numpy as np
import pytest
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PowerTransformer

from pytorch_tabular import TabularModel
from pytorch_tabular.config import DataConfig, OptimizerConfig, TrainerConfig
from pytorch_tabular.models import CategoryEmbeddingModelConfig
from pytorch_tabular.ssl_models.dae import DenoisingAutoEncoderConfig


def fake_metric(y_hat, y):
    return (y_hat - y).mean()


@pytest.mark.parametrize("multi_target", [False])
@pytest.mark.parametrize(
    "continuous_cols",
    [
        [
            "AveRooms",
            "AveBedrms",
            "Population",
            "AveOccup",
            "Latitude",
            "Longitude",
        ],
    ],
)
@pytest.mark.parametrize("categorical_cols", [["HouseAgeBin"], []])
@pytest.mark.parametrize("continuous_feature_transform", [None])
@pytest.mark.parametrize("normalize_continuous_features", [True])
@pytest.mark.parametrize("freeze_backbone", [True, False])
@pytest.mark.parametrize("target_range", [True, False])
@pytest.mark.parametrize(
    "target_transform",
    [None, PowerTransformer(), (lambda x: np.power(x, 2), lambda x: np.sqrt(x))],
)
@pytest.mark.parametrize("custom_metrics", [None, [fake_metric]])
@pytest.mark.parametrize("custom_loss", [None, torch.nn.L1Loss()])
@pytest.mark.parametrize("custom_optimizer", [None, torch.optim.Adagrad])
def test_regression(
    regression_data,
    multi_target,
    continuous_cols,
    categorical_cols,
    continuous_feature_transform,
    normalize_continuous_features,
    freeze_backbone,
    target_range,
    target_transform,
    custom_metrics,
    custom_loss,
    custom_optimizer,
):
    (train, test, target) = regression_data
    ssl, finetune = train_test_split(train, random_state=42)
    ssl_train, ssl_val = train_test_split(ssl, random_state=42)
    finetune_train, finetune_val = train_test_split(finetune, random_state=42)
    if len(continuous_cols) + len(categorical_cols) == 0:
        assert True
    else:
        data_config = DataConfig(
            target=target + ["MedInc"] if multi_target else target,
            continuous_cols=continuous_cols,
            categorical_cols=categorical_cols,
            continuous_feature_transform=continuous_feature_transform,
            normalize_continuous_features=normalize_continuous_features,
            handle_missing_values=False,
            handle_unknown_categories=False,
        )
        encoder_config = CategoryEmbeddingModelConfig(
            task="backbone",
            layers="4096-2048-512",  # Number of nodes in each layer
            activation="LeakyReLU",  # Activation between each layers
        )
        decoder_config = CategoryEmbeddingModelConfig(
            task="backbone",
            layers="512-2048-4096",  # Number of nodes in each layer
            activation="LeakyReLU",  # Activation between each layers
        )

        model_config_params = dict(
            encoder_config=encoder_config,
            decoder_config=decoder_config,
        )
        model_config = DenoisingAutoEncoderConfig(**model_config_params)
        trainer_config = TrainerConfig(
            max_epochs=1,
            checkpoints=None,
            early_stopping=None,
            gpus=None,
            fast_dev_run=True,
        )
        optimizer_config = OptimizerConfig()

        tabular_model = TabularModel(
            data_config=data_config,
            model_config=model_config,
            optimizer_config=optimizer_config,
            trainer_config=trainer_config,
        )
        tabular_model.pretrain(train=ssl_train, validation=ssl_val)
        if target_range:
            _target_range = []
            for target in data_config.target:
                _target_range.append(
                    (
                        float(train[target].min()),
                        float(train[target].max()),
                    )
                )
        else:
            _target_range = None
        finetune_model = tabular_model.create_finetune_model(
            task="regression",
            head="LinearHead",
            head_config={
                "layers": "64-32-16",
                "activation": "LeakyReLU",
            },
            trainer_config=trainer_config,
            optimizer_config=optimizer_config,
            target_range=_target_range,
            loss=custom_loss,
            metrics=custom_metrics,
            metrics_params=[{}],
            optimizer=custom_optimizer,
        )
        finetune_model.finetune(
            train=finetune_train,
            validation=finetune_val,
            freeze_backbone=freeze_backbone,
            target_transform=target_transform,
        )
        result = finetune_model.evaluate(test)
        if custom_metrics is None:
            assert "test_mean_squared_error" in result[0].keys()
        else:
            assert "test_fake_metric" in result[0].keys()
        pred_df = finetune_model.predict(test)
        assert pred_df.shape[0] == test.shape[0]


@pytest.mark.parametrize(
    "continuous_cols",
    [
        [f"feature_{i}" for i in range(54)],
    ],
)
@pytest.mark.parametrize("categorical_cols", [["feature_0_cat"]])
@pytest.mark.parametrize("continuous_feature_transform", [None])
@pytest.mark.parametrize("normalize_continuous_features", [True])
@pytest.mark.parametrize("freeze_backbone", [True, False])
def test_classification(
    classification_data,
    continuous_cols,
    categorical_cols,
    continuous_feature_transform,
    normalize_continuous_features,
    freeze_backbone,
):
    (train, test, target) = classification_data
    ssl, finetune = train_test_split(train, random_state=42)
    ssl_train, ssl_val = train_test_split(ssl, random_state=42)
    finetune_train, finetune_val = train_test_split(finetune, random_state=42)
    if len(continuous_cols) + len(categorical_cols) == 0:
        assert True
    else:
        data_config = DataConfig(
            target=target,
            continuous_cols=continuous_cols,
            categorical_cols=categorical_cols,
            continuous_feature_transform=continuous_feature_transform,
            normalize_continuous_features=normalize_continuous_features,
            handle_missing_values=False,
            handle_unknown_categories=False,
        )
        encoder_config = CategoryEmbeddingModelConfig(
            task="backbone",
            layers="4096-2048-512",  # Number of nodes in each layer
            activation="LeakyReLU",  # Activation between each layers
        )
        decoder_config = CategoryEmbeddingModelConfig(
            task="backbone",
            layers="512-2048-4096",  # Number of nodes in each layer
            activation="LeakyReLU",  # Activation between each layers
        )
        model_config_params = dict(
            encoder_config=encoder_config,
            decoder_config=decoder_config,
        )
        model_config = DenoisingAutoEncoderConfig(**model_config_params)
        trainer_config = TrainerConfig(
            max_epochs=1,
            checkpoints=None,
            early_stopping=None,
            gpus=None,
            fast_dev_run=True,
        )
        optimizer_config = OptimizerConfig()

        tabular_model = TabularModel(
            data_config=data_config,
            model_config=model_config,
            optimizer_config=optimizer_config,
            trainer_config=trainer_config,
        )
        tabular_model.pretrain(train=ssl_train, validation=ssl_val)
        finetune_model = tabular_model.create_finetune_model(
            task="classification",
            head="LinearHead",
            head_config={
                "layers": "64-32-16",
                "activation": "LeakyReLU",
            },
            trainer_config=trainer_config,
            optimizer_config=optimizer_config,
        )
        finetune_model.finetune(
            train=finetune_train,
            validation=finetune_val,
            freeze_backbone=freeze_backbone,
        )
        result = finetune_model.evaluate(test)
        assert "test_accuracy" in result[0].keys()
        pred_df = finetune_model.predict(test)
        assert pred_df.shape[0] == test.shape[0]


# @pytest.mark.parametrize(
#     "continuous_cols",
#     [
#         [
#             "AveRooms",
#             "AveBedrms",
#             "Population",
#             "AveOccup",
#             "Latitude",
#             "Longitude",
#         ],
#     ],
# )
# @pytest.mark.parametrize("categorical_cols", [["HouseAgeBin"]])
# @pytest.mark.parametrize("continuous_feature_transform", [None])
# @pytest.mark.parametrize("normalize_continuous_features", [True])
# @pytest.mark.parametrize("target_range", [False])
# @pytest.mark.parametrize("ssl_task", ["Denoising", "Contrastive"])
# @pytest.mark.parametrize("aug_task", ["cutmix", "mixup"])
# def test_ssl(
#     regression_data,
#     continuous_cols,
#     categorical_cols,
#     continuous_feature_transform,
#     normalize_continuous_features,
#     target_range,
#     ssl_task,
#     aug_task,
# ):
#     (train, test, target) = regression_data
#     if len(continuous_cols) + len(categorical_cols) == 0:
#         assert True
#     else:
#         data_config = DataConfig(
#             target=target,
#             continuous_cols=continuous_cols,
#             categorical_cols=categorical_cols,
#             continuous_feature_transform=continuous_feature_transform,
#             normalize_continuous_features=normalize_continuous_features,
#         )
#         model_config_params = dict(
#             task="ssl",
#             input_embed_dim=8,
#             num_attn_blocks=1,
#             num_heads=2,
#             ssl_task=ssl_task,
#             aug_task=aug_task,
#         )
#         if target_range:
#             _target_range = []
#             for target in data_config.target:
#                 _target_range.append(
#                     (
#                         float(train[target].min()),
#                         float(train[target].max()),
#                     )
#                 )
#             model_config_params["target_range"] = _target_range
#         model_config = FTTransformerConfig(**model_config_params)
#         trainer_config = TrainerConfig(
#             max_epochs=1,
#             checkpoints=None,
#             early_stopping=None,
#             gpus=None,
#             fast_dev_run=True,
#         )
#         optimizer_config = OptimizerConfig()

#         tabular_model = TabularModel(
#             data_config=data_config,
#             model_config=model_config,
#             optimizer_config=optimizer_config,
#             trainer_config=trainer_config,
#         )
#         tabular_model.fit(train=train, test=test)

#         result = tabular_model.evaluate(test)
#         assert "test_mean_squared_error" in result[0].keys()