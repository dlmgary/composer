from itertools import product

import pytest

from composer.datasets.synthetic_lm import SyntheticHFDataset, generate_synthetic_tokenizer


def generate_parameter_configs(keys, num_replicas=1):
    config_options = {
        "tokenizer_family": ['bert', 'gpt2'],
        "chars_per_sample": [128],
        "column_names": [['sentence'], ['sentence1', 'sentence2']],
        "num_samples": [50]
    }

    config_combinations = []
    for combo in product(*[config_options[i] for i in keys]):
        config_combinations.append([dict(zip(keys, combo)) for _ in range(num_replicas)])
    return config_combinations


@pytest.fixture
def config(request):
    return request.param


@pytest.fixture
def dataset_generator(request):
    print(request.param)
    pytest.importorskip("transformers")
    pytest.importorskip("datasets")
    pytest.importorskip("tokenizers")

    dataset_generator = SyntheticHFDataset(num_samples=request.param['num_samples'],
                                           chars_per_sample=request.param['chars_per_sample'],
                                           column_names=request.param['column_names'])
    return dataset_generator


@pytest.fixture
def dataset(dataset_generator):
    return dataset_generator.generate_dataset()


@pytest.mark.parametrize("dataset_generator, config",
                         generate_parameter_configs(['num_samples', 'chars_per_sample', 'column_names'],
                                                    num_replicas=2),
                         indirect=True)
def test_generator_sample(dataset_generator, config):
    sample = dataset_generator.generate_sample()
    assert len(sample) == config['chars_per_sample']


@pytest.mark.parametrize("dataset_generator, config",
                         generate_parameter_configs(['num_samples', 'chars_per_sample', 'column_names'],
                                                    num_replicas=2),
                         indirect=True)
def test_dataset_properties(dataset, config):
    assert len(dataset) == config['num_samples']
    assert len(dataset[config['column_names'][0]][0]) == config['chars_per_sample']
    assert dataset.column_names == (config['column_names'] + ['idx'])


@pytest.fixture
def tokenizer(dataset, config, tmp_path):
    # build the tokenizer
    tokenizer = generate_synthetic_tokenizer(config['tokenizer_family'], tmp_path=tmp_path, dataset=dataset)
    # verifying the input ids are a part of the tokenizer
    assert 'input_ids' in tokenizer.model_input_names
    return tokenizer


@pytest.fixture
def tokenized_dataset(tokenizer, dataset, config):
    # test tokenizing the dataset
    max_length = config['chars_per_sample'] * 2
    dataset = dataset.map(lambda inp: tokenizer(
        text=inp[config['column_names'][0]], padding="max_length", max_length=max_length, truncation=True),
                          batched=True,
                          num_proc=1,
                          keep_in_memory=True)
    return dataset


@pytest.mark.parametrize("dataset_generator, config",
                         generate_parameter_configs(
                             ['num_samples', 'chars_per_sample', 'column_names', 'tokenizer_family'], num_replicas=2),
                         indirect=True)
def test_tokenizer_specific_properties(tokenizer, tokenized_dataset, config):
    pytest.importorskip("transformers")
    from transformers import BertTokenizer, GPT2Tokenizer

    # verify datapoints are correct
    assert 'input_ids' in tokenized_dataset.column_names
    x = tokenized_dataset['input_ids'][0]
    max_length = config['chars_per_sample'] * 2
    assert len(x) == max_length

    # add some tokenizer-specific tests
    if config['tokenizer_family'] == "bert":
        assert x[0] == tokenizer.cls_token_id
        assert tokenizer.sep_token_id in x

    # since our tokenization max_length==chars_per_sample, we should always have padding tokens due to extra space
    assert x[-1] == tokenizer.pad_token_id

    if config['tokenizer_family'] == "bert":
        assert isinstance(tokenizer, BertTokenizer)
    elif config['tokenizer_family'] == "gpt2":
        assert isinstance(tokenizer, GPT2Tokenizer)

    assert tokenizer.pad_token_id == 0
    if config['tokenizer_family'] == "bert":
        assert tokenizer.cls_token is not None
        assert tokenizer.sep_token is not None
    elif config['tokenizer_family'] == "gpt2":
        assert tokenizer.eos_token is not None