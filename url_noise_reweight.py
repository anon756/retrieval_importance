import json
import tldextract
from pprint import pp
from retrieval_importance import learn_importance, encode_retrievals, encode_groups, v_grouped, \
    most_important_groups, least_important_groups
from retrieval_importance.utils import get_project_root
import math
import random
import numpy as np

def utility(retrieval, prediction):
    if prediction in retrieval["correct_answers"]:
        return 1.0
    else:
        return 0.0

def group(retrieved):    
    return str(retrieved)

def array_split(arr, n):
    if len(arr) > n:
        res = []
        idx = np.array_split(np.arange(len(arr)), n)
        for i in idx:
            res.append([arr[j] for j in i])
    else:
        res = [[a] for i, a in enumerate(arr)]
    return res

def generate_source_list(random_seed = 20):
    global group_num, split_num
    print("group_num: ", group_num)
    print("split_num: ", split_num)

    prob_list = [math.ceil(i/split_num)/group_num for i in range(1,1+group_num*split_num)]
    rank_list = []

    for i in range(group_num):
        random.seed(random_seed*5 + i) 
        all_number = [i for i in range(50)]
        random.shuffle(all_number)
        rank_list.extend(array_split(all_number, split_num))
    
    source_list = [(prob_list[i], rank_list[i]) for i in range(group_num*split_num)]

    random.seed(random_seed)
    random.shuffle(source_list)
    return source_list

def generate_retrival(retrivals, source_list, K, random_seed = 100, max_len = 200):
    source = []
    random.seed(random_seed)
    
    for id, now in enumerate(retrivals):
        dataset = {}
        dataset["question"] = now["question"]
        dataset["correct_answers"] = now["correct_answers"]

        list = []
        for sid, i in enumerate(source_list):
            for j in i[1]:
                if(len(now["retrieved_answers"])>j):
                    now_i = random.random()
                    if now_i <i[0]:
                        list.append((j * 100 + sid, now["retrieved_answers"][j], str(sid)))
                    else:
                        list.append((j * 100 + sid, now["noise_answers"][j], str(sid)))
        sort_list = sorted(list, key=lambda x: x[0])
        # sort_list = sort_list[:200]
        # if id == 0:
        #     print(sort_list[:10])

        dataset["retrieved_answers"] = [i[1] for i in sort_list]
        dataset["retrieved_websites"] = [i[2] for i in sort_list]
        source.append(dataset)
    return source


def cal_acc(test_set, retrievals, mapping, v, K = 10, threshold = 0.5, keep_all = False): 
    acc = 0
    for i in test_set:
        now_url = retrievals[i]['retrieved_websites']
        now_ans = retrievals[i]['retrieved_answers']
        now_correct = retrievals[i]['correct_answers']
        
        retain_list = []
        for url, ans in zip(now_url, now_ans):
            if keep_all == False: 
                if group(url) not in v:
                    continue
                if v[group(url)] < threshold:
                    continue
            retain_list.append(ans)
            if len(retain_list) == 10:
                break
        #compute the majority vote of retain_list
        vote = {}       
        for ans in retain_list:
            if ans not in vote:
                vote[ans] = 0
            vote[ans] += 1
        max_vote = 0
        max_ans = ''
        for ans in vote:
            if vote[ans] > max_vote:
                max_vote = vote[ans]
                max_ans = ans
        if max_ans in now_correct:
            acc += 1
    return acc/len(test_set)

def cal_acc_reweight_parallel(args):
    seed, test_set, retrievals, mapping, v, K, threshold, keep_all = args
    import numpy as np
    np.random.seed(seed)
    v_now = np.random.rand(len(v))
    
    acc = 0
    for i in test_set:
        now_url = retrievals[i]['retrieved_websites']
        now_ans = retrievals[i]['retrieved_answers']
        now_correct = retrievals[i]['correct_answers']
        retain_list = []
        for url, ans in zip(now_url, now_ans):
            if keep_all == False: 
                if group(url) not in v:
                    continue
                if v[group(url)] < v_now[mapping[group(url)]]:
                    continue
            retain_list.append(ans)
            if len(retain_list) == 10:
                break

        vote = {}       
        for ans in retain_list:
            if ans not in vote:
                vote[ans] = 0
            vote[ans] += 1
        max_vote = 0
        max_ans = ''
        for ans in vote:
            if vote[ans] > max_vote:
                max_vote = vote[ans]
                max_ans = ans
        if max_ans in now_correct:
            acc += 1
    return acc/len(test_set)

def cal_acc_reweight(test_set, retrievals, mapping, v, K = 10, threshold = 0.5, keep_all = False): 
    from multiprocessing import Pool
    seed = [67, 86, 55, 13, 1, 38, 81, 8, 52, 79, 10, 19, 30, 66, 36, 39, 59, 2, 21, 68, 41, 24, 31, 76, 47, 91, 99, 63, 51, 65, 26, 61]
    # run cal_acc_reweight_parallel with 32 different processes with different random seed
    with Pool(32) as p:
        acc_list = p.map(cal_acc_reweight_parallel,[(seed[i], test_set, retrievals, mapping, v, K, threshold, keep_all) for i in range(32)])
    return sum(acc_list)/len(acc_list)

def experiment(random_seed, source, K = 10, threshold = 0.5):
    
    source_list = generate_source_list(random_seed)
    retrievals = generate_retrival(source, source_list, K, random_seed)

    id_list = [i for i in range(len(retrievals))]
    random.seed(random_seed)
    random.shuffle(id_list)
    val_set = id_list[:len(retrievals)//2]
    test_set = id_list[len(retrievals)//2:]
    
    val_retrievals = [retrievals[i] for i in val_set]

    #compute the excution time of the algorithm
    encoded_retrievals, mapping = encode_retrievals(val_retrievals, "retrieved_websites", "retrieved_answers", utility)
    grouping, group_mapping = encode_groups(mapping, group)
    v = learn_importance(encoded_retrievals, k=K, learning_rate=500, num_steps=50, n_jobs=-1, grouping=grouping)
    v_per_group = v_grouped(v, grouping, group_mapping)

    acc_baseline = cal_acc(test_set, retrievals, group_mapping, v_per_group, K = K, threshold = threshold, keep_all=True)
    acc_reweight = cal_acc_reweight(test_set, retrievals, group_mapping, v_per_group, K = K)
    print(acc_baseline, acc_reweight)
    return acc_baseline, acc_reweight

def work_load(relation_name, threshold = 0.5):
    retrievals = []
    with open(f'{str(get_project_root())}/test_data/wikifact_noise/{relation_name}.jsonl') as f:
        for line in f:
            retrievals.append(json.loads(line))

    result_list = []
    seed_list = [441, 1, 469, 53, 280, 123, 219, 181, 5, 9, 199, 156, 93, 313, 28, 56, 359, 108, 8, 58, 407, 451, 322, 266, 268, 297, 12, 182, 320, 474, 296, 142, 64, 201, 32, 392, 98, 242, 344, 438, 427, 35, 77, 394, 39, 55, 330, 38, 67, 358, 237, 149, 405, 420, 411, 57, 488, 49, 42, 155, 109, 73, 331, 128]
    # seed_list = [441, 1, 469, 53, 280, 123, 219, 181]
    for random_seed in seed_list:
        result_list.append(experiment(random_seed, retrievals, K = 10, threshold = threshold))
    
    acc_baseline = sum([i[0] for i in result_list])/len(result_list)
    acc_reweight = sum([i[1] for i in result_list])/len(result_list)

    print(relation_name, acc_baseline, acc_reweight)

    return acc_baseline, acc_reweight

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('-g', type=int, default=5, help='the number of group')
    parser.add_argument('-s', type=int, default=10, help='the size of each group')

    args = parser.parse_args()

    global group_num, split_num
    group_num = args.g
    split_num = args.s

    r = ['applies_to_jurisdiction', 'author', 'award_received', 'basic_form_of_government', 'capital', 'capital_of', 'composer', 'continent', 'country', 'country_of_citizenship', 'country_of_origin', 'creator', 'currency', 'developer', 'director', 'discoverer_or_inventor', 'drug_or_therapy_used_for_treatment', 'educated_at', 'employer', 'field_of_work', 'genetic_association', 'genre', 'has_part', 'head_of_government', 'head_of_state', 'headquarters_location', 'industry', 'influenced_by', 'instance_of', 'instrument', 'language_of_work_or_name', 'languages_spoken_written_or_signed', 'located_in_the_administrative_territorial_entity', 'location', 'location_of_discovery', 'location_of_formation', 'majority_opinion_by', 'manufacturer', 'measured_physical_quantity', 'medical_condition_treated', 'member_of', 'member_of_political_party', 'member_of_sports_team', 'movement', 'named_after', 'native_language', 'occupation', 'office_held_by_head_of_government', 'official_language', 'operating_system', 'original_language_of_film_or_TV_show', 'original_network', 'owned_by', 'part_of', 'participating_team', 'place_of_birth', 'place_of_death', 'position_held', 'position_played_on_team', 'programming_language', 'recommended_unit_of_measurement', 'record_label', 'religion', 'shares_border_with', 'stock_exchange', 'subclass_of', 'subsidiary', 'symptoms_and_signs', 'twinned_administrative_body', 'work_location']
    result_list = []

    with open("./test_data/result/wiki_noise_%d_%d_64_500_50.jsonl"%(group_num, split_num), "w") as f:
        for i in r:
            acc_baseline, acc_reweight = work_load(i)
            result_list.append((acc_baseline, acc_reweight))
            tmp = {'relation':i, 'acc_baseline':acc_baseline, 'acc_reweight':acc_reweight}
            f.write(json.dumps(tmp) + "\n")
            f.flush()
        acc_baseline = sum([i[0] for i in result_list])/len(result_list)
        acc_reweight = sum([i[1] for i in result_list])/len(result_list)
        print("average", acc_baseline, acc_reweight)
        f.write(json.dumps({'relation':'average', 'acc_baseline':acc_baseline, 'acc_reweight':acc_reweight}) + "\n")

