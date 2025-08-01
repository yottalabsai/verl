# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
The abstract base class defining the interface for model training engines.
"""

from typing import Callable

import torch

from verl import DataProto


class BaseEngine:
    """
    Abstract base class defining the interface for model training engines.

    Engine implementations must subclass BaseEngine and provide concrete behavior for all methods.
    """

    def __init__(self, config):
        """
        Initialize the BaseEngine.

        Args:
            config: Configuration object containing parameters for engine setup.
        """
        raise NotImplementedError

    def init_model(self):
        """
        Instantiate or load the model, optimizer, and learning rate scheduler.

        Should prepare all components necessary for training or evaluation.
        """
        raise NotImplementedError

    def train_mode(self):
        """
        Context manager entry for switching the engine and model into training mode.

        Usage:
            with engine.train_mode():
                # runs in training mode
        """
        raise NotImplementedError

    def eval_mode(self):
        """
        Context manager entry for switching the engine and model into evaluation mode.

        Usage:
            with engine.eval_mode():
                # runs in evaluation mode
        """
        raise NotImplementedError

    def infer_batch(
        self,
        data: DataProto,
        post_fn: Callable[[DataProto, torch.Tensor], tuple[torch.Tensor, dict[str, torch.Tensor]]],
    ) -> dict[str, torch.Tensor]:
        """
        Perform inference on a mini batch of data.

        Args:
            data: The input data for inference, typically containing tensors and metadata.
            post_fn: A post-processing function that takes a micro-batch and predictions as input,
                     and returns a tuple containing processed predictions and a dictionary of outputs.

        Returns:
            dict[str, torch.Tensor]: A dictionary containing the predictions for the entire batch.
        """
        raise NotImplementedError

    def train_batch(
        self,
        data: DataProto,
        loss_fn: Callable[[DataProto, torch.Tensor], tuple[torch.Tensor, dict[str, torch.Tensor]]],
    ) -> dict[str, torch.Tensor]:
        """
        Perform a training step on a mini-batch of data.

        Args:
            data (DataProto): The input data for training, typically containing tensors and metadata.
            loss_fn (Callable): A function that computes the loss and metrics given a micro-batch and predictions.

        Returns:
            dict[str, torch.Tensor]: A dictionary containing the aggregated training metrics for the mini-batch.
        """
        raise NotImplementedError

    def optimizer_zero_grad(self):
        """
        Zero out gradients of all parameters before starting a new backward pass.
        """
        raise NotImplementedError

    def optimizer_step(self):
        """
        Perform an optimization step to update model parameters based on accumulated gradients.

        Returns:
            grad_norm (float): The norm of the gradients before clipping or update.
        """
        raise NotImplementedError

    def lr_scheduler_step(self):
        """
        Advance the learning rate scheduler by one step.

        Returns:
            current_lr (float or list[float]): Updated learning rate(s).
        """
        raise NotImplementedError

    def shard_data(self, data):
        """
        Shard or partition data for distributed training or parallel execution.

        Args:
            data: Data structure to be sharded across devices/workers.

        Returns:
            Sharded data in the same format as input.
        """
        raise NotImplementedError

    def unshard_data(self, data):
        """
        Reconstruct or gather sharded data back to a unified format.

        Args:
            data: Sharded data structure to reconstruct.

        Returns:
            Unsharded, combined data.
        """
        raise NotImplementedError

    def to(self, device: str, model: bool = True, optimizer: bool = True):
        """
        Move model parameters, optimizer states, or both to the specified device.

        Args:
            device: Target device identifier.
            model: If True, move the model.
            optimizer: If True, move the optimizer states.
        """
        raise NotImplementedError

    def save_checkpoint(self, local_path, hdfs_path=None, global_step=0, max_ckpt_to_keep=None):
        """
        Save model, optimizer, and scheduler states to a checkpoint.

        Args:
            local_path: Local filesystem path to save checkpoint.
            hdfs_path: Optional HDFS path to copy checkpoint.
            global_step: Integer training step number for naming.
            max_ckpt_to_keep: Maximum number of recent checkpoints to retain.
        """
        raise NotImplementedError

    def load_checkpoint(self, local_path, hdfs_path=None, del_local_after_load=True):
        """
        Load model, optimizer, and scheduler states from a checkpoint.

        Args:
            local_path: Local filesystem path of the checkpoint.
            hdfs_path: Optional HDFS path where checkpoint is stored.
            del_local_after_load: Whether to delete local copy after loading.
        """
        raise NotImplementedError


class EngineRegistry:
    """
    A registry for managing and instantiating different types of training engines.

    This class uses a dictionary to store engine classes, mapping a string key to each class.
    It provides a decorator `register` to add new engines to the registry and a `new` method
    to create an instance of a registered engine.
    """

    _engines = {}

    @classmethod
    def register(cls, key):
        """
        A class method decorator that registers an engine class with a given key.

        This allows for dynamic instantiation of engine classes by their registered key.

        Args:
            key (str): The identifier to associate with the engine class.

        Returns:
            A decorator function that takes an engine class and registers it.
        """

        def decorator(engine_class):
            assert issubclass(engine_class, BaseEngine)
            cls._engines[key] = engine_class
            return engine_class

        return decorator

    @classmethod
    def new(cls, key, *args, **kwargs):
        """
        Function to create a new training engine instance based on the provided config.
        Args:
            key: A configuration object containing the engine key and other settings.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Returns:
            engine: An instance of the training engine corresponding to the config.
        Raises:
            NotImplementedError: If the engine key in the config does not match any known engines.
        """
        if key in cls._engines:
            return cls._engines[key](*args, **kwargs)
        else:
            raise NotImplementedError(f"Unknown engine: {key}")
