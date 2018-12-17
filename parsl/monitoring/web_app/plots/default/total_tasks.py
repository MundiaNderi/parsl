import numpy as np
import pandas as pd
import plotly.graph_objs as go
import dash_core_components as dcc
import dash_html_components as html
from parsl.monitoring.web_app.utils import timestamp_to_int, num_to_timestamp, DB_DATE_FORMAT
from parsl.monitoring.web_app.app import get_db, close_db
from parsl.monitoring.web_app.plots.base_plot import BasePlot


class TotalTasksPlot(BasePlot):
    def __init__(self, plot_id, plot_args):
        super().__init__(plot_id, plot_args)

    def setup(self, run_id, columns=20):
        sql_conn = get_db()
        df_status = pd.read_sql_query('SELECT run_id, task_id, task_status_name, timestamp FROM task_status WHERE run_id=(?)',
                                      sql_conn, params=(run_id, ))
        close_db()

        min_time = timestamp_to_int(min(df_status['timestamp']))
        max_time = timestamp_to_int(max(df_status['timestamp']))

        time_step = int((max_time - min_time) / columns)
        minutes = time_step // 60
        seconds = time_step % 60

        return [html.P('Bin width'),
                html.Label(htmlFor='bin_width_minutes', children='Minutes'),
                dcc.Input(id='bin_width_minutes', type='number', min=0, value=minutes),
                html.Label(htmlFor='bin_width_seconds', children='Seconds'),
                dcc.Input(id='bin_width_seconds', type='number', min=0, value=seconds)]

    def plot(self, minutes, seconds, run_id):
        sql_conn = get_db()
        df_status = pd.read_sql_query('SELECT run_id, task_id, task_status_name, timestamp FROM task_status WHERE run_id=(?)',
                                      sql_conn, params=(run_id, ))
        df_task = pd.read_sql_query('SELECT task_id, task_func_name FROM task WHERE run_id=(?)',
                                    sql_conn, params=(run_id, ))

        close_db()

        min_time = timestamp_to_int(min(df_status['timestamp']))
        max_time = timestamp_to_int(max(df_status['timestamp']))
        time_step = 60 * minutes + seconds

        x_axis = []
        for i in range(min_time, max_time + time_step, time_step):
            x_axis.append(num_to_timestamp(i).strftime(DB_DATE_FORMAT))

        # Fill up dict "apps" like: {app1: [#task1, #task2], app2: [#task4], app3: [#task3]}
        apps_dict = dict()
        for i in range(len(df_task)):
            row = df_task.iloc[i]
            if row['task_func_name'] in apps_dict:
                apps_dict[row['task_func_name']].append(row['task_id'])
            else:
                apps_dict[row['task_func_name']] = [row['task_id']]

        def y_axis_setup(value):
            items = []
            for app, tasks in apps_dict.items():
                tmp = []
                task = df_status[df_status['task_id'].isin(tasks)]
                for i in range(len(x_axis) - 1):
                    x = task['timestamp'] >= x_axis[i]
                    y = task['timestamp'] < x_axis[i + 1]
                    tmp.append(sum(task.loc[x & y]['task_status_name'] == value))
                items = np.sum([items, tmp], axis=0)

            return items

        y_axis_done = y_axis_setup('done')
        y_axis_failed = y_axis_setup('failed')

        return go.Figure(data=[go.Bar(x=x_axis[:-1],
                                      y=y_axis_done,
                                      name='done'),
                               go.Bar(x=x_axis[:-1],
                                      y=y_axis_failed,
                                      name='failed')],
                         layout=go.Layout(xaxis=dict(tickformat='%m-%d\n%H:%M:%S',
                                                     autorange=True,
                                                     title='Time'),
                                          yaxis=dict(tickformat=',d',
                                                     title='Running tasks.' ' Bin width: ' + num_to_timestamp(time_step).strftime('%Mm%Ss')),
                                          annotations=[
                                              dict(
                                                  x=0,
                                                  y=1.12,
                                                  showarrow=False,
                                                  text='Total Done: ' + str(sum(y_axis_done)),
                                                  xref='paper',
                                                  yref='paper'
                                              ),
                                              dict(
                                                  x=0,
                                                  y=1.05,
                                                  showarrow=False,
                                                  text='Total Failed: ' + str(sum(y_axis_failed)),
                                                  xref='paper',
                                                  yref='paper'
                                              ),
                                          ],
                                          barmode='stack',
                                          title="Total tasks"))


class TotalTasksMultiplePlot(BasePlot):
    def __init__(self, plot_id, plot_args):
        super().__init__(plot_id, plot_args)

    def setup(self, run_id, columns=20):
        sql_conn = get_db()
        df_status = pd.read_sql_query('SELECT run_id, task_id, task_status_name, timestamp FROM task_status WHERE run_id=(?)',
                                      sql_conn, params=(run_id, ))
        close_db()

        min_time = timestamp_to_int(min(df_status['timestamp']))
        max_time = timestamp_to_int(max(df_status['timestamp']))

        time_step = int((max_time - min_time) / columns)
        minutes = time_step // 60
        seconds = time_step % 60

        return [html.P('Bin width'),
                html.Label(htmlFor='bin_width_minutes', children='Minutes'),
                dcc.Input(id='bin_width_minutes', type='number', min=0, value=minutes),
                html.Label(htmlFor='bin_width_seconds', children='Seconds'),
                dcc.Input(id='bin_width_seconds', type='number', min=0, value=seconds)]

    def plot(self, minutes, seconds, apps, run_id):
        sql_conn = get_db()
        df_status = pd.read_sql_query('SELECT run_id, task_id, task_status_name, timestamp FROM task_status WHERE run_id=(?)',
                                      sql_conn, params=(run_id, ))

        if type(apps) is dict:
            apps = ['', apps['label']]
        elif len(apps) == 1:
            apps.append('')

        df_task = pd.read_sql_query('SELECT task_id, task_func_name FROM task WHERE run_id=(?) AND task_func_name IN {apps}'.format(apps=tuple(apps)),
                                    sql_conn, params=(run_id, ))

        close_db()

        min_time = timestamp_to_int(min(df_status['timestamp']))
        max_time = timestamp_to_int(max(df_status['timestamp']))
        time_step = 60 * minutes + seconds

        x_axis = []
        for i in range(min_time, max_time + time_step, time_step):
            x_axis.append(num_to_timestamp(i).strftime(DB_DATE_FORMAT))

        # Fill up dict "apps" like: {app1: [#task1, #task2], app2: [#task4], app3: [#task3]}
        apps_dict = dict()
        for i in range(len(df_task)):
            row = df_task.iloc[i]
            if row['task_func_name'] in apps_dict:
                apps_dict[row['task_func_name']].append(row['task_id'])
            else:
                apps_dict[row['task_func_name']] = [row['task_id']]

        def y_axis_setup(value):
            items = []
            for app, tasks in apps_dict.items():
                tmp = []
                task = df_status[df_status['task_id'].isin(tasks)]
                for i in range(len(x_axis) - 1):
                    x = task['timestamp'] >= x_axis[i]
                    y = task['timestamp'] < x_axis[i + 1]
                    tmp.append(sum(task.loc[x & y]['task_status_name'] == value))
                items = np.sum([items, tmp], axis=0)

            return items

        y_axis_done = y_axis_setup('done')
        y_axis_failed = y_axis_setup('failed')

        return go.Figure(data=[go.Bar(x=x_axis[:-1],
                                      y=y_axis_done,
                                      name='done' + ' (' + str(sum(y_axis_done)) + ')'),
                               go.Bar(x=x_axis[:-1],
                                      y=y_axis_failed,
                                      name='failed' + ' (' + str(sum(y_axis_failed)) + ')')],
                         layout=go.Layout(xaxis=dict(tickformat='%m-%d\n%H:%M:%S',
                                                     autorange=True,
                                                     title='Time'),
                                          yaxis=dict(tickformat=',d',
                                                     title='Running tasks.' ' Bin width: ' + num_to_timestamp(time_step).strftime('%Mm%Ss')),
                                          barmode='stack',
                                          title="Total tasks"))
