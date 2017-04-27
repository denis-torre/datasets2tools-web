import re, json
import pandas as pd
pd.set_option('max.colwidth', -1)

class CannedAnalysisDatabase:
    
    def __init__(self, engine):
        self.engine = engine

    # def fetch_tables(self):
        # self.tool = pd.read_sql_query('SELECT * FROM tool', self.engine, index_col='id')
        # self.dataset = pd.read_sql_query('SELECT * FROM dataset', self.engine, index_col='id')
        # self.repository = pd.read_sql_query('SELECT * FROM repository', self.engine, index_col='id')
        # self.term = pd.read_sql_query('SELECT * FROM term', self.engine, index_col='id')
        # self.canned_analysis = pd.read_sql_query('SELECT * FROM canned_analysis', self.engine, index_col='id')
        # self.canned_analysis_metadata = pd.read_sql_query('SELECT * FROM canned_analysis_metadata', self.engine, index_col='id')
        
    def search_analyses_by_keyword(self, keywords):
        # matching_search_results = pd.read_sql_query('SELECT DISTINCT canned_analysis_fk FROM canned_analysis_metadata WHERE canned_analysis_fk IN (SELECT canned_analysis_fk FROM canned_analysis_metadata WHERE value = "' + '") AND canned_analysis_fk IN (SELECT canned_analysis_fk FROM canned_analysis_metadata WHERE value = "'.join(keywords)+'")', self.engine)
        similar_search_results = pd.read_sql_query('SELECT DISTINCT canned_analysis_fk FROM canned_analysis_metadata WHERE canned_analysis_fk IN (SELECT canned_analysis_fk FROM canned_analysis_metadata WHERE value LIKE "%%' + '%%") AND canned_analysis_fk IN (SELECT canned_analysis_fk FROM canned_analysis_metadata WHERE value LIKE "%%'.join(keywords)+'%%")', self.engine)
        ids = similar_search_results['canned_analysis_fk'].tolist()
        return ids

    def make_canned_analysis_table(self, ids, limit=25):
        ids = ids[:limit]
        canned_analyses = pd.read_sql_query('SELECT ca.id as id, tool_name, tool_icon_url, tool_homepage_url, tool_description, repository_name, repository_homepage_url, repository_icon_url, repository_description, dataset_description, dataset_title, dataset_landing_url, dataset_accession, canned_analysis_url, tool_screenshot_url FROM canned_analysis ca LEFT JOIN dataset d ON d.id=ca.dataset_fk LEFT JOIN tool t ON t.id=ca.tool_fk LEFT JOIN repository r ON r.id=d.repository_fk WHERE ca.id IN ('+', '.join([str(x) for x in ids])+')', self.engine, index_col='id')
        metadata = pd.read_sql_query('SELECT canned_analysis_fk, term_name, term_description, value FROM canned_analysis_metadata cam LEFT JOIN term t on t.id = cam.term_fk WHERE term_name != "description" AND cam.canned_analysis_fk IN ('+', '.join([str(x) for x in ids])+') ORDER BY term_name', self.engine)
        descriptions = dict(pd.read_sql_query('SELECT canned_analysis_fk, value FROM canned_analysis_metadata cam LEFT JOIN term t on t.id = cam.term_fk WHERE term_name = "description"', self.engine, index_col='canned_analysis_fk'))['value']
        result_list = []
        for index, rowData in canned_analyses.iterrows():
            tool_html = '<div class="tool-cell"><a class="tool-cell-logo" href="'+rowData['tool_homepage_url']+'"><img class="tool-cell-logo-icon" src="'+rowData['tool_icon_url']+'"><span class="tool-cell-logo-title">'+rowData['tool_name']+'</span></a><span class="tool-cell-text">'+rowData['tool_description']+'</span></div>'
            dataset_html = '<div class="dataset-cell"><a class="dataset-cell-logo" href="'+rowData['dataset_landing_url']+'""><img class="dataset-cell-logo-icon" src="'+rowData['repository_icon_url']+'"><span class="dataset-cell-logo-title">'+rowData['dataset_accession']+'</span></a><span class="dataset-cell-text">'+rowData['dataset_title']+' <sup><i class="fa fa-info-circle fa-1x"  aria-hidden="true" data-toggle="tooltip" data-placement="right" data-html="true" title="'+rowData['dataset_description']+'"></i></sup></span></div>'
            analysis_hyml = '<div class="analysis-cell"><a href="'+rowData['canned_analysis_url']+'"><img class="analysis-cell-icon" src="'+rowData['tool_screenshot_url']+'"></a><div class="analysis-cell-text">'+descriptions[index]+'.</div></div>'
            metadata_html = '<div class="metadata-cell">'+'<br>'.join(['<span class="metadata-cell-tag">'+metadataRowData['term_name'].replace('_', ' ').title()+'</span><sup>&nbsp<i class="fa fa-info-circle fa-1x"  aria-hidden="true" data-toggle="tooltip" data-placement="top" data-html="true" data-animation="false" title="'+metadataRowData['term_description']+'"></i></sup>: <span class="metadata-cell-value">'+metadataRowData['value']+'</span>' for metadataIndex, metadataRowData in metadata[metadata['canned_analysis_fk'] == index].iterrows()]) + '</div>'
            result_list.append([tool_html, dataset_html, analysis_hyml, metadata_html])
        result_dataframe = pd.DataFrame(result_list, columns=['Tool', 'Dataset', 'Analysis', 'Metadata'])
        return result_dataframe.to_html(escape=False, index=False, classes='canned-analysis-table').encode('ascii', 'ignore')

    def search_datasets_by_keyword(self, keywords):
        similar_search_results = pd.read_sql_query('SELECT id FROM dataset WHERE id IN (SELECT id FROM dataset WHERE CONCAT(dataset_accession, " ", dataset_title, " ", dataset_description) LIKE "%%' + '%%") AND id IN (SELECT id FROM dataset WHERE CONCAT(dataset_accession, " ", dataset_title, " ", dataset_description) LIKE "%%'.join(keywords)+'%%")', self.engine)
        ids = similar_search_results['id'].tolist()
        return ids

    def make_dataset_table(self, ids, limit=25):
        ids = ids[:limit]
        analysis_counts = pd.read_sql_query('SELECT dataset_accession, tool_name, tool_icon_url, tool_description, tool_homepage_url, count(dataset_accession) AS count FROM canned_analysis ca LEFT JOIN dataset d on d.id=ca.dataset_fk LEFT JOIN tool t on t.id = ca.tool_fk WHERE d.id in ('+', '.join([str(x) for x in ids])+') GROUP BY dataset_accession, tool_name ORDER BY dataset_accession ASC, count DESC', self.engine)
        datasets = pd.read_sql_query('SELECT * FROM dataset d LEFT JOIN repository r on r.id = d.repository_fk WHERE d.id in ('+', '.join([str(x) for x in ids])+')', self.engine)
        datasets = datasets.set_index('dataset_accession', drop=False).loc[analysis_counts.groupby('dataset_accession').sum().sort_values('count', ascending=False).index].reset_index(drop=True)
        return_letter = lambda x: 'e' if x > 1 else 'i'
        result_list = []
        for index, rowData in datasets.iterrows():
            dataset_html = '<div class="dataset-title-cell"><a href="'+rowData['dataset_landing_url']+'" class="dataset-title-cell-accession">'+rowData['dataset_accession']+'</a><div class="dataset-title-cell-text">'+rowData['dataset_title']+'</div></div>'
            description_html = '<div class="dataset-description-cell">'+rowData['dataset_description']+'</div>'
            repository_html = '<div class="dataset-repository-cell"><a href="'+rowData['repository_homepage_url']+'"><img class="dataset-repository-cell-icon" src="'+rowData['repository_icon_url']+'"></a><div class="dataset-repository-cell-text">'+rowData['repository_name']+' <sup><i class="fa fa-info-circle fa-1x"  aria-hidden="true" data-toggle="tooltip" data-placement="bottom" data-html="true" data-animation="false" title="'+rowData['repository_description']+'"></i></sup></div></div>'
            analysis_html = '<div class="dataset-tool-analysis-count-cell">'+''.join('<div class="dataset-tool-analysis-count"><a class="dataset-tool-analysis-count-tool-link" href="'+countRowData['tool_homepage_url']+'"><img class="dataset-tool-analysis-count-icon" src="'+countRowData['tool_icon_url']+'"></a><div class="dataset-tool-analysis-count-text"><a href="'+countRowData['tool_homepage_url']+'" class="dataset-tool-analysis-count-title">'+countRowData['tool_name']+'</a><sup> <i class="fa fa-info-circle fa-1x" aria-hidden="true" data-toggle="tooltip" data-placement="top" data-html="true" data-animation="false" title="'+countRowData['tool_description']+'"></i></sup>: <a href="http://localhost:5000/datasets2tools/advanced_search?query=((object%20IS%20analyses)%20AND%20dataset_accession%20IS%20%22'+rowData['dataset_accession']+'%22)%20AND%20tool_name%20IS%20%22'+countRowData['tool_name']+'%22" class="dataset-tool-analysis-count-analysis">' + str(countRowData['count']) + ' analys'+return_letter(countRowData['count'])+'s</a></div></div>' for countIndex, countRowData in analysis_counts[analysis_counts['dataset_accession']==rowData['dataset_accession']].iterrows()) + '</div>'
            result_list.append([dataset_html, description_html, repository_html, analysis_html])
        result_dataframe = pd.DataFrame(result_list, columns=['Dataset', 'Description', 'Repository', 'Analyses']).set_index('Dataset', drop=False)#.loc[analysis_counts['dataset_accession'].unique()]
        return result_dataframe.to_html(escape=False, index=False, classes='dataset-table').encode('ascii', 'ignore')

    def search_tools_by_keyword(self, keywords):
        similar_search_results = pd.read_sql_query('SELECT id FROM tool WHERE id IN (SELECT id FROM tool WHERE CONCAT(tool_name, " ", tool_description) LIKE "%%' + '%%") AND id IN (SELECT id FROM tool WHERE CONCAT(tool_name, " ", tool_description) LIKE "%%'.join(keywords)+'%%")', self.engine)
        ids = similar_search_results['id'].tolist()
        return ids

    def make_tool_table(self, ids, limit=25):
        ids = ids[:limit]
        tools = pd.read_sql_query('SELECT tool_name, tool_icon_url, tool_homepage_url, tool_description, count(*)-1 AS count FROM tool t LEFT JOIN canned_analysis ca on t.id = ca.tool_fk WHERE t.id IN ('+', '.join([str(x) for x in ids])+') GROUP BY tool_name ORDER BY count desc', self.engine)
        result_list = []
        for indew, rowData in tools.iterrows():
            tool_icon_html = '<a href="'+rowData['tool_homepage_url']+'" class="tool-icon-cell"><img class="tool-icon-cell-logo" src="'+rowData['tool_icon_url']+'"><div class="tool-icon-cell-text">'+rowData['tool_name']+'</div></a>'
            tool_description_html = '<div class="tool-description-cell">'+rowData['tool_description']+'</div>'
            analysis_html = '<a href="#" class="tool-analysis-count-cell">' + str(rowData['count']) + '</div>'
            result_list.append([tool_icon_html, tool_description_html, analysis_html])
        result_dataframe = pd.DataFrame(result_list, columns=['Tool', 'Description', 'Analyses'])
        return result_dataframe.to_html(escape=False, index=False, classes='tool-table').encode('ascii', 'ignore')

    def get_keyword_json(self, ignore_keywords=['pert_ids', 'description', 'ctrl_ids', 'creeds_id', 'smiles', 'mm_gene_symbol', 'chdir_norm', 'top_genes']):
        values = pd.read_sql_query('SELECT DISTINCT term_name, value, count(*) AS count FROM canned_analysis_metadata cam LEFT JOIN term t on t.id=cam.term_fk WHERE term_name NOT IN ("'+'", "'.join(ignore_keywords)+'") GROUP BY term_name, value HAVING count > 10 ORDER BY count ASC', self.engine, index_col='term_name')
        tree_dict = {'name': 'Canned Analyses', 'children': [{'name': term_name.replace('_', ' ').title(), 'children': [{'name': rowData['value'], 'size': rowData['count']} for index, rowData in values.loc[term_name].iterrows()]} for term_name in values.index.unique()]}
        return tree_dict

    def get_keyword_count(self, ignore_keywords=['pert_ids', 'description', 'ctrl_ids', 'creeds_id', 'smiles', 'mm_gene_symbol', 'chdir_norm', 'top_genes']):
        keyword_count = pd.read_sql_query('SELECT DISTINCT term_name, value, count(*) AS count FROM canned_analysis_metadata cam LEFT JOIN term t on t.id=cam.term_fk WHERE term_name NOT IN ("'+'", "'.join(ignore_keywords)+'") GROUP BY term_name, value', self.engine, index_col='term_name')

    def get_term_names(self, object_type):
        canned_analysis_metadata_terms = pd.read_sql_query('SELECT term_name FROM term', self.engine)['term_name'].tolist()
        dataset_terms = ['dataset_accession', 'dataset_title', 'dataset_description', 'repository', 'repository_description']
        tool_terms = ['tool_name', 'tool_description']
        if object_type == 'Analyses':
            term_list = ['All Fields']+canned_analysis_metadata_terms+dataset_terms+tool_terms
            return '\n'.join([x.replace('_', ' ').title() for x in term_list])
        elif object_type == 'Datasets':
            term_list = ['All Fields']+dataset_terms
            return '\n'.join([x.replace('_', ' ').title() for x in term_list])
        elif object_type == 'Tools':
            term_list = ['All Fields']+tool_terms
            return '\n'.join([x.replace('_', ' ').title() for x in term_list])

    def advanced_search(self, advanced_query):

        if 'AND' not in advanced_query:
            raise ValueError('No conditions specified.')

        object_type = advanced_query.split('object IS ')[-1].split(')')[0]
        advanced_query = '('+advanced_query.lower().replace('object is', 'SELECT id FROM').replace(' not contains ', ' NOT LIKE "%').replace(' contains ', ' LIKE "%').replace(' and ', ' AND ').replace(' or ', ' OR ').replace(' is not', ' != ').replace(' is ', ' = ')+')'
        
        if any([x in advanced_query for x in ['drop', 'truncate']]):
            raise ValueError('Not allowed.')

        advanced_query = re.sub(r'%"(.+?(?="\)))', r'%%\1%%', advanced_query)
        if object_type == 'analyses':
            advanced_query = advanced_query.replace('analyses) AND', 'canned_analysis_metadata cam LEFT JOIN term ON term.id=cam.term_fk LEFT JOIN canned_analysis ca on ca.id=cam.canned_analysis_fk LEFT JOIN dataset d on d.id=ca.dataset_fk LEFT JOIN tool on tool.id=ca.tool_fk WHERE').replace('all_fields', 'value').replace('(', '').replace(')', '').replace('SELECT id', 'SELECT DISTINCT ca.id')
            term_names = pd.read_sql_query('SELECT * FROM term', self.engine)['term_name'].tolist()
            for term_name in term_names:
                advanced_query = re.sub(r'(%(term_name)s)([^"]*"[^"]*")' % locals(), r'ca.id IN (SELECT canned_analysis_fk FROM canned_analysis_metadata cam LEFT JOIN term t ON t.id=cam.term_fk WHERE `term_name`="\1" AND `value`\2)', advanced_query)
        elif object_type == 'datasets':
            advanced_query = advanced_query.replace('datasets) AND', 'dataset d LEFT JOIN repository r on r.id=d.repository_fk WHERE').replace('(', '').replace(')', '').replace('all_fields', 'CONCAT_WS(" ", dataset_accession, dataset_title, dataset_description)').replace('SELECT id', 'SELECT DISTINCT d.id')
        elif object_type == 'tools':
            advanced_query = advanced_query.replace('tools) AND', 'tool WHERE').replace('(', '').replace(')', '').replace('all_fields', 'CONCAT_WS(" ", tool_name, tool_description)')
        advanced_query += ' LIMIT 25'
        search_results = pd.read_sql_query(advanced_query, self.engine)
        if len(search_results.index) > 0:
            return search_results['id'].tolist()
        else:
            return []

    def get_stored_data(self):
        stored_data = {x: pd.read_sql_query('SELECT * FROM %(x)s' % locals(), self.engine, index_col='id') for x in ['dataset', 'tool', 'term']}
        return stored_data

    def object_search(self, object_type, id):
        if object_type == 'dataset':
            return json.dumps(pd.read_sql_query('SELECT * FROM dataset d LEFT JOIN repository r on r.id = d.repository_fk WHERE d.id = {id}'.format(**locals()), self.engine).to_dict(orient='index')[0])
        elif object_type == 'tool':
            return json.dumps(pd.read_sql_query('SELECT * FROM tool WHERE id = {id}'.format(**locals()), self.engine).to_dict(orient='index')[0])
        else:
            return ''
