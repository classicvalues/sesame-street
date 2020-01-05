from bottle import route, run, template, static_file, request
import bottle
import os
import json
from collections import defaultdict
from nn import *
from config import *

bottle.TEMPLATE_PATH.insert(0, 'views')

# pylint: disable=no-member


@route('/<filename:path>')
def send_static(filename):
    return static_file(filename, root='static/')


@route('/', method='GET')
def index():
    return template(
        'index.html',
        tasks=['alphanli', 'hellaswag', 'piqa', 'siqa'],
        models=['roberta', 'bert', 'xlnet'],
        embedders=['ai2', 'st'],
        filters={},
        task="alphanli",
        embedder="ai2",
        result={},
        total=0,
        margins=[]
    )


@route('/', method='POST')
def retrieve():
    print(request.forms.__dict__)
    task = request.forms.get('task')
    embedder = request.forms.get('embedder')

    filters = {}

    for model in ['roberta', 'bert', 'xlnet']:
        if request.forms.get(model, None) is not None:
            filters[model] = request.forms.get(model, None)
    print(filters)

    margins = heatmap(filters, task)
    train_dataset, dev_dataset = load_dataset(task)

    valid_indices = filtering(filters, task)
    result = {}
    closest = get_closest(filters, task, embedder)



    for i, model in enumerate(filters):
        preds, probs, labels = load_predictions(predictions[model][task])
        for j, (pred, prob, label) in enumerate(zip(preds, probs, labels)):
            if j not in valid_indices: continue
            if j not in result:
                result[j] = dev_dataset[j]
            result[j]["choices"][pred - datasets[task]["offset"]]["models"].append({
                "model": model,
                "margin": "-" if pred == label else prob[pred - datasets[task]["offset"]] - prob[label - datasets[task]["offset"]],
                "closest": [
                    {
                        "ctx": train_dataset[int(x) // datasets[task]["num_choices"]]["ctx"],
                        "choice": train_dataset[int(x) // datasets[task]["num_choices"]]["choices"][int(x) % datasets[task]["num_choices"]]
                    } for x in closest[i][j * datasets[task]["num_choices"] + pred - datasets[task]["offset"]]
                ]
            })


    return template(
        'index.html',
        tasks=['alphanli', 'hellaswag', 'piqa', 'siqa'],
        models=['roberta', 'bert', 'xlnet'],
        embedders=['ai2', 'st'],
        filters=filters,
        task=task,
        embedder=embedder,
        result=result,
        total=len(dev_dataset),
        margins=margins,
    )


def filtering(filters, task):

    valid_indices = set()

    for j, model in enumerate(filters):
        model_indices = set()
        preds, probs, labels = load_predictions(predictions[model][task])

        for i, (pred, prob, label) in enumerate(zip(preds, probs, labels)):

            if pred == label and filters[model] == "correct":
                model_indices.add(i)
            elif pred != label and filters[model] == "wrong":
                model_indices.add(i)
        valid_indices = model_indices if j == 0 else valid_indices.intersection(model_indices)
    return valid_indices

def heatmap(filters, task):

    margins = []
    for i, model in enumerate(filters):
        preds, probablities, labels = load_predictions(predictions[model][task])
        margin = []
        for j, (pred, prob, label) in enumerate(zip(preds, probablities, labels)):
            margin.append([j, i, "-"] if pred == label else [j, i, prob[pred - datasets[task]["offset"]] - prob[label - datasets[task]["offset"]]])
        print(sum( 1 if x[-1] == "-" else 0 for x in margin) / len(margin))
        margins.extend(margin)
    return margins

def get_closest(filters, task, embedder):

    results = []

    for i, model in enumerate(filters):
        print(closest_indices[task][model][embedder])
        results.append(np.loadtxt(closest_indices[task][model][embedder]))

    return results

if __name__ == "__main__":
    run(host='localhost', port=7777, reloader=True)
