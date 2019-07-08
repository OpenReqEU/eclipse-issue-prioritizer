# coding: utf-8

from application.util import helper
import matplotlib.pyplot as plt
import datetime
from collections import Counter
from sklearn.model_selection import train_test_split as tts
import numpy as np


plt.style.use('ggplot')


def is_relevant_comment(c):
    key = "raw_text" if "raw_text" in c.keys() else "text"
    if c[key].startswith("Cloned from:") or c[key].startswith("New Gerrit change created") \
    or c[key].startswith("Gerrit change"):
        return False
    return True


def train_test_split(requirements, n_years_training=1.5, n_years_testing=1.0, n_end_years=1.0):
    """
    now = datetime.datetime.now()
    requs = list(filter(lambda r: helper.estimated_difference_in_years(
        datetime.datetime.strptime(r.last_change_time, "%Y-%m-%dT%H:%M:%SZ"), now) <= 5.0, requirements.values()))
    return tts(requs, [0]*len(requs), test_size=0.2, random_state=42)
    """
    now = datetime.datetime.now()
    train_requirements = filter(lambda r: helper.estimated_difference_in_years(
        datetime.datetime.strptime(r.last_change_time, "%Y-%m-%dT%H:%M:%SZ"),
        now) > (n_years_testing + n_end_years) and helper.estimated_difference_in_years(
        datetime.datetime.strptime(r.last_change_time, "%Y-%m-%dT%H:%M:%SZ"), now) <= (n_years_training + n_years_testing + n_end_years), requirements.values())
    test_requirements = filter(lambda r: helper.estimated_difference_in_years(
        datetime.datetime.strptime(r.last_change_time, "%Y-%m-%dT%H:%M:%SZ"),
        now) > n_end_years and helper.estimated_difference_in_years(
        datetime.datetime.strptime(r.last_change_time, "%Y-%m-%dT%H:%M:%SZ"), now) <= (n_years_testing + n_end_years), requirements.values())
    return list(train_requirements), list(test_requirements), None, None


def extract_requirements_by_products_and_components(requirements, is_consider_comment_creators=False):
    product_component_requirements = {}
    product_component_contributors = {}
    contributors_involved_in_number_of_requirements = Counter()
    all_product_components = set()
    all_products = set()
    for r in requirements:
        assert r.assigned_to is not None and r.assigned_to != "", "Contributor: {}".format(r.assigned_to)
        if r.product not in product_component_requirements:
            product_component_requirements[r.product] = {}
        if r.component not in product_component_requirements[r.product]:
            product_component_requirements[r.product][r.component] = {}
        product_component_requirements[r.product][r.component][r.id] = r

        all_products.add(r.product)
        if r.product not in product_component_contributors:
            product_component_contributors[r.product] = {}
        if r.component not in product_component_contributors[r.product]:
            product_component_contributors[r.product][r.component] = set()
        product_component_contributors[r.product][r.component].add(r.assigned_to)
        contributors_involved_in_number_of_requirements[r.assigned_to] += 1
        if is_consider_comment_creators:
            for c in r.comments:
                if not is_relevant_comment(c):
                    continue
                if c["creator"] != r.assigned_to:
                    product_component_contributors[r.product][r.component].add(c["creator"])
                    contributors_involved_in_number_of_requirements[c["creator"]] += 1
        all_product_components.add("{}_{}".format(r.product, r.component))
    return product_component_requirements, product_component_contributors, \
           contributors_involved_in_number_of_requirements, all_product_components, all_products


def reasonable_product_components_list(product_component_requirements, product_component_contributors, min_num_requirements=100, min_num_contributors=20):
    reasonable_product_components = set()
    for product_name, product_components in product_component_requirements.items():
        assignee_product_components = product_component_contributors[product_name]
        for product_component_name, requirements in product_components.items():
            contributors = assignee_product_components[product_component_name]
            if len(requirements) >= min_num_requirements and len(contributors) >= min_num_contributors:
                reasonable_product_components.add("{}_{}".format(product_name, product_component_name))
    return reasonable_product_components


def print_product_component_summary(product_component_requirements, reasonable_product_components):
    print("Summary of requirements/contributors per product and component")
    n_remaining_components = 0
    components_contributor_activity = {}
    for product_name, product_components in product_component_requirements.items():
        counter = 0
        for product_component_name, requirements in product_components.items():
            key = "{}_{}".format(product_name, product_component_name)
            if key not in reasonable_product_components:
                continue
            if counter == 0:
                print("Product: {}".format(product_name))
            counter += 1
            n_remaining_components += 1

            contributor_activity = {}
            for r in requirements.values():
                if r.assigned_to not in contributor_activity:
                    contributor_activity[r.assigned_to] = 0
                contributor_activity[r.assigned_to] += 1
            components_contributor_activity[product_component_name] = Counter(contributor_activity)
            print("    {}\t-> {}\t\tContributors:\t{}".format(product_component_name, len(requirements), len(contributor_activity)))
            #print("               {}".format(Counter(contributor_activity).most_common(3)))

    print("Remaining number of components: {}".format(n_remaining_components))
    print("-" * 80)


def group_contributors(train_requirements, test_requirements, is_consider_comment_creators):
    _, _, contributors_involved_in_number_of_requirements, _ = extract_requirements_by_products_and_components(
        train_requirements, is_consider_comment_creators)

    new_train_requirements = []
    for r in train_requirements:
        # if contributors_involved_in_number_of_requirements[r.assigned_to] <= 20:
        #    continue
        assert r.assigned_to in contributors_involved_in_number_of_requirements
        if contributors_involved_in_number_of_requirements[r.assigned_to] > 30:
            r.assigned_to = "HIGH"
        elif contributors_involved_in_number_of_requirements[r.assigned_to] > 10:
            r.assigned_to = "MID"
        elif contributors_involved_in_number_of_requirements[r.assigned_to] > 5:
            r.assigned_to = "LOW"
        elif contributors_involved_in_number_of_requirements[r.assigned_to] > 1:
            r.assigned_to = "VERY_LOW"
        else:
            r.assigned_to = "VERY_VERY_LOW"
        new_train_requirements += [r]

    train_requirements = new_train_requirements

    new_test_requirements = []
    for r in test_requirements:
        if r.assigned_to not in contributors_involved_in_number_of_requirements:
            continue
        # if contributors_involved_in_number_of_requirements[r.assigned_to] <= 20:
        #    continue
        if contributors_involved_in_number_of_requirements[r.assigned_to] > 40:
            r.assigned_to = "HIGH"
        elif contributors_involved_in_number_of_requirements[r.assigned_to] > 10:
            r.assigned_to = "MID"
        elif contributors_involved_in_number_of_requirements[r.assigned_to] > 5:
            r.assigned_to = "LOW"
        elif contributors_involved_in_number_of_requirements[r.assigned_to] > 1:
            r.assigned_to = "VERY_LOW"
        else:
            r.assigned_to = "VERY_VERY_LOW"
        new_test_requirements += [r]

    test_requirements = new_test_requirements

    return train_requirements, test_requirements


def print_basic_statistics(requirements):
    n_title_length = 0
    n_title_words_length = 0
    n_desc_length = 0
    n_desc_words_length = 0
    n_desc_requs = 0
    all_contributors = Counter()
    for r in requirements.values():
        n_title_length += len(r.summary)
        n_title_words_length += len(r.summary.split(" "))
        assert (len(r.assigned_to) > 0)
        all_contributors[r.assigned_to] += 1
        if len(r.comments) > 0:
            key = "raw_text" if "raw_text" in r.comments[0].keys() else "text"
            n_desc_length += len(r.comments[0][key])
            n_desc_words_length += len(r.comments[0][key].split(" "))
            n_desc_requs += 1

    avg_title_length = float(n_title_length) / float(len(requirements))
    avg_desc_length = float(n_desc_length) / float(n_desc_requs)
    avg_title_words_length = float(n_title_words_length) / float(len(requirements))
    avg_desc_words_length = float(n_desc_words_length) / float(n_desc_requs)
    print("=" * 80)
    print("Average title length: {}".format(avg_title_length))
    print("Average description length: {}".format(avg_desc_length))
    print("Average title words length: {}".format(avg_title_words_length))
    print("Average description words length: {}".format(avg_desc_words_length))
    print("Number of requirements: {}".format(len(requirements)))
    print("Number of contributors: {}".format(len(all_contributors)))
    temp = list(all_contributors.values())
    issues_per_contributor = np.array(temp)
    print("MEAN issues per contributor: {}".format(issues_per_contributor.mean()))
    print("STD issues per contributor: {}".format(issues_per_contributor.std()))
    print("MEDIAN issues per contributor: {}".format(np.median(issues_per_contributor)))
    print("Number of contributors who resolved only one issue: {}".format(len(list(filter(lambda n: n == 1.0, temp)))))

    n_total_comments = 0
    for n_comments in map(lambda r: r.number_of_comments, requirements.values()):
        n_total_comments += n_comments
    print("Number of total comments: {}".format(n_total_comments))
    print("=" * 80)


def print_contributors_component_statistics(train_prod_comp_contributors, reasonable_prod_comps):
    assignees_per_component = Counter()
    for product_name, product_components in train_prod_comp_contributors.items():
        counter = 0
        for product_component_name, assignees in product_components.items():
            key = "{}_{}".format(product_name, product_component_name)
            if key not in reasonable_prod_comps:
                continue
            counter += 1

            for _ in assignees:
                assignees_per_component[product_component_name] += 1
    print("-" * 80)
    assignees_per_component = np.array(list(assignees_per_component.values()))
    print("MEAN Contributors per component: {}".format(assignees_per_component.mean()))
    print("STD Contributors per component: {}".format(assignees_per_component.std()))
    print("-" * 80)


def plot_contributors_activity_histogram(dataset_name, requirements, is_consider_comment_creators):
    _, _, contributors_involved_in_number_of_requirements, all_prod_comps, _ = extract_requirements_by_products_and_components(requirements.values(), is_consider_comment_creators)
    import matplotlib.pyplot as plt
    #plt.style.use('ggplot')
    histogram = {}
    for (assignee, number_of_resolved_requirements) in contributors_involved_in_number_of_requirements.items():
        if number_of_resolved_requirements not in histogram:
            histogram[number_of_resolved_requirements] = 0
        histogram[number_of_resolved_requirements] += 1

    plt.hist(list(contributors_involved_in_number_of_requirements.values()), 300,
             range=(1, 400), log=True, color="0.0")
    plt.grid(True, which="both", ls="-", color="0.8")
    plt.title(dataset_name.upper())
    plt.xlabel("Number of Resolved Issues")
    plt.ylabel("Number of Contributors")
    plt.show()

    # plt.plot(histogram.keys(), histogram.values())
    # plt.title("Developer Activity Histogram")
    # plt.xlabel("Number of Requirements")
    # plt.ylabel("Number of Contributors")
    # plt.axis([1, 1500, 0, 50])
    # plt.show()
    # import sys;sys.exit()


def keras_plot_loss_accuracy(history):
    history_dict = history.history
    history_dict.keys()

    # ['val_loss', 'val_acc', 'val_binary_precision', 'val_binary_recall', 'val_binary_f1_score',
    #  'loss', 'acc', 'binary_precision', 'binary_recall', 'binary_f1_score']
    acc = history_dict['acc']
    val_acc = history_dict['val_acc']
    loss = history_dict['loss']
    val_loss = history_dict['val_loss']

    #p = history_dict['binary_precision']
    p = history_dict['precision']
    #val_p = history_dict['val_binary_precision']
    val_p = history_dict['val_precision']

    #r = history_dict['binary_recall']
    r = history_dict['recall']
    #val_r = history_dict['val_binary_recall']
    val_r = history_dict['val_recall']

    #f1 = history_dict['binary_f1_score']
    f1 = history_dict['f1_score']
    #val_f1 = history_dict['val_binary_f1_score']
    val_f1 = history_dict['val_f1_score']

    epochs = range(1, len(acc) + 1)
    # "bo" is for "blue dot"
    plt.plot(epochs, loss, 'bo', label='Training loss')
    # b is for "solid blue line"
    plt.plot(epochs, val_loss, 'r', label='Validation loss')
    plt.title('Training and validation loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.show()

    plt.plot(epochs, acc, 'bo', label='Training acc')
    plt.plot(epochs, val_acc, 'b', label='Validation acc')
    plt.title('Training and validation accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.show()

    #plt.plot(epochs, p, 'bo', label='Training Precision')
    plt.plot(epochs, val_p, 'b', label='Validation Precision')
    #plt.plot(epochs, r, 'go', label='Training Recall')
    plt.plot(epochs, val_r, 'g', label='Validation Recall')
    #plt.plot(epochs, f1, 'ro', label='Training F1')
    plt.plot(epochs, val_f1, 'r', label='Validation F1')
    plt.title('Training and validation accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.show()

