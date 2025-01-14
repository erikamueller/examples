#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author(s): Ai Chen  & Erika Müller
# date: 26.04.2022
# Machine Translation FS2022
# MT Exercise 3: Task 3 Implement command line prompt for text generation
# Testcases:
# Testing of generate.py with additional input prompt:
# 	Testcase 1: input of 4 valid words --> take the four words as input
# 	Testcase 2: input of 1 valid word --> take this word as input
# 	Testcase 3: input of 1 invalid word --> take default random input
# 	Testcase 4: input of 4 valid words, but 2nd word is not valid --> take only the 3 valid words as input
# 	Testcase 5: input of 2 invalid words --> take default random input
# 	Testcase 6: no user input prompt --> take default random input
###############################################################################
# Language Modeling on Wikitext-2 or any other text for example the novel
#              Emma by Jane Austen
#
# This file generates new sentences sampled from the language model. The user
# can optionally enter a prompt for the first word or words of the text.
#
###############################################################################
import argparse
import torch

import data

parser = argparse.ArgumentParser(description='PyTorch Wikitext-2 Language Model')
# Model parameters.
parser.add_argument('--data', type=str, default='./data/wikitext-2',
                    help='location of the data corpus')
parser.add_argument('--checkpoint', type=str, default='./model.pt',
                    help='model checkpoint to use')
parser.add_argument('--outf', type=str, default='generated.txt',
                    help='output file for generated text')
parser.add_argument('--words', type=int, default='1000',
                    help='number of words to generate')
parser.add_argument('--seed', type=int, default=1111,
                    help='random seed')
parser.add_argument('--cuda', action='store_true',
                    help='use CUDA')
parser.add_argument('--temperature', type=float, default=1.0,
                    help='temperature - higher will increase diversity')
parser.add_argument('--log-interval', type=int, default=100,
                    help='reporting interval')
# additional command line argument according to task description exercise 3
parser.add_argument('--input', type=str,
                    help='optional prompt of text input')
args = parser.parse_args()

# Set the random seed manually for reproducibility.
torch.manual_seed(args.seed)
if torch.cuda.is_available():
    if not args.cuda:
        print("WARNING: You have a CUDA device, so you should probably run with --cuda.")

device = torch.device("cuda" if args.cuda else "cpu")

if args.temperature < 1e-3:
    parser.error("--temperature has to be greater or equal 1e-3.")

with open(args.checkpoint, 'rb') as f:
    model = torch.load(f, map_location=device)
model.eval()

corpus = data.Corpus(args.data)
ntokens = len(corpus.dictionary)

# check for input prompt --> delete in the end
if args.input:
    print(f'Your input was: {args.input}.')

is_transformer_model = hasattr(model, 'model_type') and model.model_type == 'Transformer'
if not is_transformer_model:
    hidden = model.init_hidden(1)

input_tensor_list = []  # to store the tensors of the input prompt words

# check if input prompt words are in the vocabulary. Convert the valid ones in a tensor
if args.input:
    words = args.input.split()
    for word in words:
        try:
            input_tensor_list.append(torch.tensor([[corpus.dictionary.word2idx[word]]]))
        # if word is not in vocabulary just skip it
        except KeyError:
            print(f'The word "{word}" is not part of the vocabulary and will therefore be removed from the input.')
            continue

input_word_count = len(input_tensor_list)   # count of valid words in the input prompt

# in case there are valid input words hand the tensor of the first word to the input
# if there are no valid words an the input prompt or the --input argument was not entered by user,
# generate a random integer tensor from the vocabulary to hand to the input
if input_word_count > 0:
    input = input_tensor_list[0].to(device)
else:
    input = torch.randint(ntokens, (1, 1), dtype=torch.long).to(device)  # eg. tensor([[3940]])

with open(args.outf, 'w') as outf:
    with torch.no_grad():  # no tracking history
        for i in range(args.words):
            # transformer model --> no changes required according to task description
            if is_transformer_model:
                output = model(input, False)
                word_weights = output[-1].squeeze().div(args.temperature).exp().cpu()
                word_idx = torch.multinomial(word_weights, 1)[0]
                word_tensor = torch.Tensor([[word_idx]]).long().to(device)
                input = torch.cat([input, word_tensor], 0)
            # rnn model --> adapted to possibility of additional optional input prompt words
            else:
                output, hidden = model(input, hidden)
                word_weights = output.squeeze().div(args.temperature).exp().cpu()
                word_idx = torch.multinomial(word_weights, 1)[0]
                # in case of input prompt words overwrite word_idx with the index tensor of the input word
                if input_word_count > 0:
                    word_idx = input_tensor_list[i][0][0]
                    input_word_count -= 1
                input.fill_(word_idx)

            word = corpus.dictionary.idx2word[word_idx]

            outf.write(word + ('\n' if i % 20 == 19 else ' '))

            if i % args.log_interval == 0:
                print('| Generated {}/{} words'.format(i, args.words))
